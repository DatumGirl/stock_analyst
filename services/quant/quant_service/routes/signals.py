"""Technical composite signal computation and persistence.

Computes a deterministic rank_score (0–100) from RSI, MACD, SMA trend, and
5-day momentum, then upserts one row per ticker per day into the signals table.
No LLM calls — all numbers are derived from price history.
"""
from __future__ import annotations

import datetime
import math
from typing import Any

import httpx
import numpy as np
from fastapi import APIRouter, HTTPException

from ..config import settings
from ..engines.indicators import macd_histogram, rsi, sma

router = APIRouter(prefix="/signals", tags=["signals"])

MODEL_VERSION = "technical_composite_v1"


def _safe(v: Any) -> float:
    try:
        f = float(v)
        return 0.0 if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return 0.0


async def _fetch_prices(ticker: str, days: int = 65) -> list[float]:
    if not settings.supabase_url:
        return []
    url = (
        f"{settings.supabase_url}/rest/v1/prices_daily"
        f"?ticker=eq.{ticker}&select=adj_close&order=date.desc&limit={days}"
    )
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers, timeout=10.0)
    if res.status_code != 200:
        return []
    # Reverse so array is oldest-first
    return [_safe(r["adj_close"]) for r in reversed(res.json())]


def _compute_score(prices: list[float]) -> tuple[float, float, float]:
    """Return (rank_score 0–100, probability 0–1, confidence 0–1).

    Scoring:
      Base 50 + RSI component (±20) + MACD component (±12)
            + SMA-20 trend (±8) + SMA-50 trend (±5) + momentum (±5)
    Max = 100, min = 0.
    """
    if len(prices) < 20:
        return 50.0, 0.50, 0.30

    arr = np.array(prices, dtype=np.float64)
    score = 50.0

    rsi_val = rsi(arr, 14)
    if not math.isnan(rsi_val):
        if rsi_val < 30:
            score += 20       # deeply oversold → contrarian bullish
        elif rsi_val < 40:
            score += 10
        elif rsi_val > 70:
            score -= 20       # overbought → near-term risk
        elif rsi_val > 60:
            score -= 5

    hist = macd_histogram(arr)
    if not math.isnan(hist):
        score += 12 if hist > 0 else -12

    current = arr[-1]
    sma20 = sma(arr, 20)
    sma50 = sma(arr, 50) if len(arr) >= 50 else sma20
    score += 8 if current > sma20 else -8
    score += 5 if current > sma50 else -5

    if len(arr) >= 6 and arr[-6] != 0:
        momentum = (arr[-1] - arr[-6]) / arr[-6]
        score += min(5.0, max(-5.0, round(momentum * 100, 1)))

    score = max(0.0, min(100.0, round(score, 2)))
    probability = round(score / 100.0, 4)
    confidence = 0.55 if len(prices) >= 50 else 0.45

    return score, probability, confidence


async def _upsert(row: dict[str, Any]) -> None:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        return
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{settings.supabase_url}/rest/v1/signals?on_conflict=ticker,date,model_version",
            headers=headers,
            json=[row],
            timeout=10.0,
        )
    if res.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Signal upsert failed: {res.text[:200]}")


@router.post("/{ticker}", summary="Compute and persist a technical composite signal")
async def compute_signal(ticker: str) -> dict[str, Any]:
    ticker = ticker.upper()

    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    prices = await _fetch_prices(ticker)
    if not prices:
        raise HTTPException(status_code=404, detail=f"No prices found for {ticker} — run ingest first")

    rank_score, probability, confidence = _compute_score(prices)
    today = datetime.date.today().isoformat()

    row: dict[str, Any] = {
        "ticker": ticker,
        "date": today,
        "model_version": MODEL_VERSION,
        "probability": probability,
        "rank_score": rank_score,
        "confidence": confidence,
        "is_forecast": True,
    }
    await _upsert(row)

    return {
        "ticker": ticker,
        "date": today,
        "rank_score": rank_score,
        "probability": probability,
        "confidence": confidence,
        "model_version": MODEL_VERSION,
    }

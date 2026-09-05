"""Portfolio snapshot computation — total value, day return, basic health score."""
from __future__ import annotations

import datetime
import math
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException

from ..config import settings

router = APIRouter(prefix="/snapshot", tags=["snapshot"])


def _safe(v: Any) -> float:
    try:
        f = float(v)
        return 0.0 if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return 0.0


async def _get(path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    if not settings.supabase_url:
        return []
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"{settings.supabase_url}/rest/v1/{path}",
            headers=headers,
            params=params,
            timeout=15.0,
        )
    return res.json() if res.status_code == 200 else []


async def _upsert(table: str, row: dict[str, Any], on_conflict: str) -> None:
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
        "Content-Type": "application/json",
        "Prefer": "resolution=merge-duplicates,return=minimal",
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{settings.supabase_url}/rest/v1/{table}?on_conflict={on_conflict}",
            headers=headers,
            json=[row],
            timeout=15.0,
        )
    if res.status_code not in (200, 201):
        raise HTTPException(status_code=500, detail=f"Snapshot upsert failed: {res.text[:300]}")


@router.post("/{portfolio_id}", summary="Compute and persist a portfolio snapshot")
async def compute_snapshot(portfolio_id: str) -> dict[str, Any]:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HTTPException(status_code=503, detail="Supabase not configured")

    # ── Positions ─────────────────────────────────────────────────────────────
    positions = await _get(
        "positions",
        {"portfolio_id": f"eq.{portfolio_id}", "select": "ticker,quantity,cost_basis"},
    )
    if not positions:
        raise HTTPException(status_code=404, detail="No positions found for this portfolio")

    tickers = list({p["ticker"] for p in positions})
    tickers_csv = ",".join(tickers)

    # ── Latest 2 days of prices for all tickers in one query ─────────────────
    price_rows = await _get(
        "prices_daily",
        {
            "ticker": f"in.({tickers_csv})",
            "select": "ticker,date,adj_close",
            "order": "date.desc",
            "limit": str(len(tickers) * 3),
        },
    )

    # Group into {ticker: [price_desc, ...]}
    price_map: dict[str, list[float]] = {}
    for row in price_rows:
        t = row["ticker"]
        price_map.setdefault(t, []).append(_safe(row["adj_close"]))

    # ── Ticker sectors ────────────────────────────────────────────────────────
    sector_rows = await _get(
        "tickers",
        {
            "symbol": f"in.({tickers_csv})",
            "select": "symbol,sector",
        },
    )
    ticker_sector: dict[str, str] = {
        r["symbol"]: r["sector"] for r in sector_rows if r.get("sector")
    }

    # ── Compute metrics ───────────────────────────────────────────────────────
    total_value = 0.0
    total_cost = 0.0
    day_return_sum = 0.0
    day_return_count = 0
    position_values: dict[str, float] = {}

    for pos in positions:
        ticker = pos["ticker"]
        qty = _safe(pos["quantity"])
        cost = _safe(pos["cost_basis"])
        prices = price_map.get(ticker, [])

        latest = prices[0] if prices else 0.0
        prev = prices[1] if len(prices) > 1 else latest

        pos_value = qty * latest
        position_values[ticker] = pos_value
        total_value += pos_value
        total_cost += qty * cost

        if prev > 0 and latest > 0:
            day_return_sum += (latest - prev) / prev
            day_return_count += 1

    day_return = day_return_sum / day_return_count if day_return_count > 0 else 0.0
    period_return = (total_value - total_cost) / total_cost if total_cost > 0 else 0.0

    # ── Sector exposures ──────────────────────────────────────────────────────
    sector_values: dict[str, float] = {}
    for ticker, value in position_values.items():
        sector = ticker_sector.get(ticker, "Unknown")
        sector_values[sector] = sector_values.get(sector, 0.0) + value

    exposures: dict[str, float] = {}
    if total_value > 0:
        exposures = {
            sector: round(value / total_value, 4)
            for sector, value in sector_values.items()
        }

    # ── Health score (simplified until ML pipeline is live) ──────────────────
    n = len(positions)
    diversification_score = min(100, max(20, n * 8))   # 13+ positions → 100
    data_coverage = int(100 * day_return_count / max(n, 1))
    quality_score = min(100, max(50, data_coverage))
    # Penalise if concentrated (< 5 positions) or over-concentrated (> 20)
    risk_score = 75 if 5 <= n <= 20 else 60 if n < 5 else 70
    health_score = (diversification_score + quality_score + risk_score) // 3

    risk_level = (
        "low" if risk_score >= 80
        else "moderate" if risk_score >= 65
        else "elevated" if risk_score >= 50
        else "high"
    )

    today = datetime.date.today().isoformat()

    snapshot: dict[str, Any] = {
        "portfolio_id": portfolio_id,
        "date": today,
        "total_value": round(total_value, 2),
        "day_return": round(day_return, 6),
        "period_return": round(period_return, 6),
        "health_score": health_score,
        "diversification_score": diversification_score,
        "risk_score": risk_score,
        "quality_score": quality_score,
        "risk_level": risk_level,
        "exposures": exposures,
        "risk_metrics": {},
        "target_probability": 0.50,
        "target_probability_delta": 0.0,
    }

    await _upsert("portfolio_snapshots", snapshot, "portfolio_id,date")
    return snapshot

"""Technical Agent — fetches price history and computes technical indicators."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import numpy as np
from pydantic import BaseModel


class TechnicalData(BaseModel):
    ticker: str
    current_price: float | None
    price_change_pct: float | None
    rsi_14: float | None
    macd_line: float | None
    macd_signal: float | None
    macd_hist: float | None
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    atr_14: float | None
    vwap: float | None
    relative_volume: float | None
    support: float | None
    resistance: float | None
    trend: str | None        # uptrend / downtrend / sideways
    momentum: str | None     # strong / moderate / weak / overbought / oversold
    as_of: str
    warnings: list[str]


class AgentResult(BaseModel):
    data: TechnicalData
    sources: list[str]
    as_of: str
    warnings: list[str]


class TechnicalAgent:
    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        self._url = supabase_url
        self._key = supabase_key

    def _headers(self) -> dict[str, str]:
        return {"apikey": self._key, "Authorization": f"Bearer {self._key}"}

    async def run(self, ticker: str, client: httpx.AsyncClient) -> AgentResult:
        from quant_engine import indicators  # inline import to avoid circular deps

        warnings: list[str] = []
        now = datetime.now(timezone.utc).isoformat()

        resp = await client.get(
            f"{self._url}/rest/v1/prices_daily",
            params={
                "ticker": f"eq.{ticker}",
                "order": "date.desc",
                "limit": "252",
                "select": "date,open,high,low,close,volume",
            },
            headers=self._headers(),
        )

        rows: list[dict[str, Any]] = []
        if resp.status_code == 200:
            rows = list(reversed(resp.json()))

        if len(rows) < 20:
            warnings.append(f"Insufficient price data for {ticker} ({len(rows)} days)")
            data = TechnicalData(
                ticker=ticker, current_price=None, price_change_pct=None,
                rsi_14=None, macd_line=None, macd_signal=None, macd_hist=None,
                sma_20=None, sma_50=None, sma_200=None,
                atr_14=None, vwap=None, relative_volume=None,
                support=None, resistance=None,
                trend=None, momentum=None,
                as_of=now, warnings=warnings,
            )
            return AgentResult(data=data, sources=[], as_of=now, warnings=warnings)

        closes = np.array([float(r["close"]) for r in rows])
        highs = np.array([float(r["high"]) for r in rows])
        lows = np.array([float(r["low"]) for r in rows])
        vols = np.array([float(r["volume"]) for r in rows])

        rsi_arr = indicators.rsi(closes)
        macd_line_arr, signal_arr, hist_arr = indicators.macd(closes)
        sma20 = indicators.sma(closes, 20)
        sma50 = indicators.sma(closes, 50)
        sma200 = indicators.sma(closes, 200)
        atr_arr = indicators.atr(highs, lows, closes)
        vwap_arr = indicators.vwap(highs, lows, closes, vols)
        rel_vol = indicators.relative_volume(vols)
        support, resistance = indicators.support_resistance(closes, window=20)

        current = float(closes[-1])
        prev = float(closes[-2]) if len(closes) > 1 else current
        pct_change = (current - prev) / prev if prev != 0 else None

        rsi_val = _nanf(rsi_arr[-1])
        sma200_val = _nanf(sma200[-1])

        trend: str | None = None
        if sma200_val is not None:
            if current > sma200_val * 1.02:
                trend = "uptrend"
            elif current < sma200_val * 0.98:
                trend = "downtrend"
            else:
                trend = "sideways"

        momentum: str | None = None
        if rsi_val is not None:
            if rsi_val > 70:
                momentum = "overbought"
            elif rsi_val < 30:
                momentum = "oversold"
            elif rsi_val > 60:
                momentum = "strong"
            elif rsi_val < 40:
                momentum = "weak"
            else:
                momentum = "moderate"

        data = TechnicalData(
            ticker=ticker,
            current_price=current,
            price_change_pct=pct_change,
            rsi_14=rsi_val,
            macd_line=_nanf(macd_line_arr[-1]),
            macd_signal=_nanf(signal_arr[-1]),
            macd_hist=_nanf(hist_arr[-1]),
            sma_20=_nanf(sma20[-1]),
            sma_50=_nanf(sma50[-1]),
            sma_200=sma200_val,
            atr_14=_nanf(atr_arr[-1]),
            vwap=_nanf(vwap_arr[-1]),
            relative_volume=_nanf(rel_vol[-1]),
            support=support,
            resistance=resistance,
            trend=trend,
            momentum=momentum,
            as_of=rows[-1]["date"],
            warnings=warnings,
        )
        return AgentResult(data=data, sources=[f"supabase/prices_daily/{ticker}"], as_of=data.as_of, warnings=warnings)


def _nanf(v: float) -> float | None:
    import math
    return None if (v is None or math.isnan(v)) else float(v)

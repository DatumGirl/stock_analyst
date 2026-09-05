"""Market indices — fetch recent OHLCV for major exchange benchmarks."""
from __future__ import annotations

import asyncio
import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/market", tags=["market"])

# Exchange → display name + benchmark ticker
EXCHANGES: dict[str, dict[str, str]] = {
    "SP500":   {"name": "S&P 500",    "ticker": "^GSPC",  "exchange": "NYSE"},
    "NASDAQ":  {"name": "NASDAQ",     "ticker": "^IXIC",  "exchange": "NASDAQ"},
    "DOW":     {"name": "Dow Jones",  "ticker": "^DJI",   "exchange": "NYSE"},
    "FTSE":    {"name": "FTSE 100",   "ticker": "^FTSE",  "exchange": "LSE"},
    "NIKKEI":  {"name": "Nikkei 225", "ticker": "^N225",  "exchange": "TSE"},
    "DAX":     {"name": "DAX",        "ticker": "^GDAXI", "exchange": "XETRA"},
    "HANGSENG":{"name": "Hang Seng",  "ticker": "^HSI",   "exchange": "HKEX"},
    "SSE":     {"name": "Shanghai",   "ticker": "000001.SS","exchange": "SSE"},
}


def _fetch_indices(keys: list[str], period: str) -> list[dict[str, Any]]:
    """Blocking yfinance fetch — run in executor."""
    import yfinance as yf

    results = []
    for key in keys:
        meta = EXCHANGES.get(key)
        if not meta:
            continue
        try:
            t = yf.Ticker(meta["ticker"])
            hist = t.history(period=period, interval="1d", auto_adjust=True)
            if hist.empty:
                continue
            prices = [
                {"date": ts.strftime("%Y-%m-%d"), "close": round(float(row["Close"]), 2)}
                for ts, row in hist.iterrows()
                if row.get("Close") is not None
            ]
            if not prices:
                continue
            latest = prices[-1]["close"]
            prev   = prices[-2]["close"] if len(prices) > 1 else latest
            change_pct = round((latest - prev) / prev * 100, 3) if prev else 0.0
            results.append({
                "key":        key,
                "name":       meta["name"],
                "exchange":   meta["exchange"],
                "ticker":     meta["ticker"],
                "latest":     latest,
                "change_pct": change_pct,
                "prices":     prices,
            })
        except Exception:
            pass
    return results


@router.get("/indices")
async def get_indices(
    keys: str = "SP500,NASDAQ,DOW",
    period: str = "1mo",
) -> dict[str, Any]:
    """Return price history for requested exchange indices.

    Args:
        keys: Comma-separated exchange keys (SP500, NASDAQ, DOW, FTSE, NIKKEI, DAX, HANGSENG, SSE).
        period: yfinance period string (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y).
    """
    requested = [k.strip().upper() for k in keys.split(",") if k.strip()]
    unknown = [k for k in requested if k not in EXCHANGES]
    if unknown:
        raise HTTPException(status_code=400, detail=f"Unknown exchange keys: {unknown}. Valid: {list(EXCHANGES)}")

    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, _fetch_indices, requested, period)
    return {
        "indices": data,
        "available": [
            {"key": k, "name": v["name"], "exchange": v["exchange"]}
            for k, v in EXCHANGES.items()
        ],
    }

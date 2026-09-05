"""Return and risk metrics endpoint."""
from __future__ import annotations

import datetime
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException, Query

from ..config import settings
from ..engines import returns as eng
from ..models import QuantResult, ReturnMetrics

router = APIRouter(prefix="/metrics", tags=["metrics"])

PERIOD_DAYS: dict[str, int] = {
    "1D": 1,
    "1W": 5,
    "1M": 21,
    "3M": 63,
    "6M": 126,
    "YTD": -1,  # computed dynamically
    "1Y": 252,
    "3Y": 756,
    "5Y": 1260,
}


async def _fetch_prices(ticker: str, days: int) -> list[dict[str, Any]]:
    """Fetch OHLCV from Supabase. Returns list of {date, close} rows."""
    try:
        import httpx
    except ImportError:
        return []

    if not settings.supabase_url or not settings.supabase_service_role_key:
        return []

    url = (
        f"{settings.supabase_url}/rest/v1/prices_daily"
        f"?ticker=eq.{ticker}&select=date,adj_close&order=date.desc&limit={days + 10}"
    )
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers, timeout=10.0)
    if res.status_code != 200:
        return []
    return res.json()


@router.get("/{ticker}", response_model=QuantResult)
async def get_metrics(
    ticker: str,
    period: str = Query("1M", description="1D/1W/1M/3M/6M/YTD/1Y/3Y/5Y"),
    benchmark: str = Query("SPY", description="Benchmark ticker for beta"),
) -> QuantResult:
    days = PERIOD_DAYS.get(period.upper(), 21)
    if days == -1:
        ytd_start = datetime.date(datetime.date.today().year, 1, 1)
        days = (datetime.date.today() - ytd_start).days

    rows = await _fetch_prices(ticker, days)
    if not rows:
        # Return stub when no Supabase is configured — useful for local dev
        stub = ReturnMetrics(
            ticker=ticker,
            period=period,
            total_return=0.0,
            annualised_return=0.0,
            volatility_30d=0.0,
            volatility_252d=0.0,
            beta=None,
            sharpe=None,
            sortino=None,
            max_drawdown=0.0,
            var_95=0.0,
            cvar_95=0.0,
            as_of=datetime.date.today().isoformat(),
        )
        return QuantResult(
            data=stub.model_dump(),
            sources=[],
            as_of=datetime.date.today().isoformat(),
            warnings=[f"No price data available for {ticker}"],
        )

    prices = np.array([float(r["adj_close"]) for r in reversed(rows)], dtype=np.float64)
    rets = eng.daily_returns(prices)

    bench_rows = await _fetch_prices(benchmark, days)
    bench_prices = np.array([float(r["adj_close"]) for r in reversed(bench_rows)], dtype=np.float64) if bench_rows else np.array([])
    bench_rets = eng.daily_returns(bench_prices) if len(bench_prices) > 1 else np.array([])

    result = ReturnMetrics(
        ticker=ticker,
        period=period,
        total_return=eng.total_return(prices),
        annualised_return=eng.annualise(eng.total_return(prices), len(rets)),
        volatility_30d=eng.volatility(rets, window=30),
        volatility_252d=eng.volatility(rets),
        beta=eng.beta(rets, bench_rets) if len(bench_rets) > 0 else None,
        sharpe=eng.sharpe_ratio(rets),
        sortino=eng.sortino_ratio(rets),
        max_drawdown=eng.max_drawdown(prices),
        var_95=eng.var_historical(rets),
        cvar_95=eng.cvar_historical(rets),
        as_of=rows[0]["date"],
    )

    return QuantResult(
        data=result.model_dump(),
        sources=[f"supabase:prices_daily:{ticker}"],
        as_of=rows[0]["date"],
        warnings=[],
    )

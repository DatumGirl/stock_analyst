"""Portfolio-level risk metrics endpoint."""
from __future__ import annotations

import datetime
from typing import Any

import numpy as np
from fastapi import APIRouter, HTTPException

from ..config import settings
from ..engines import returns as eng
from ..models import PortfolioRiskInput, PortfolioRiskOutput, QuantResult

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


async def _fetch_returns_matrix(tickers: list[str], days: int = 252) -> np.ndarray:
    """Fetch returns for all tickers and align dates. Returns (n_assets × n_days)."""
    import httpx

    if not settings.supabase_url:
        return np.zeros((len(tickers), days))

    tickers_param = ",".join(f"'{t}'" for t in tickers)
    url = (
        f"{settings.supabase_url}/rest/v1/prices_daily"
        f"?ticker=in.({tickers_param})&select=ticker,date,adj_close"
        f"&order=date.desc&limit={days * len(tickers) + 50}"
    )
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers, timeout=15.0)
    if res.status_code != 200:
        return np.zeros((len(tickers), days))

    rows: list[dict[str, Any]] = res.json()
    from collections import defaultdict
    by_ticker: dict[str, list[float]] = defaultdict(list)
    for row in sorted(rows, key=lambda r: r["date"]):
        by_ticker[row["ticker"]].append(float(row["adj_close"]))

    min_len = min(len(v) for v in by_ticker.values()) if by_ticker else 0
    if min_len < 2:
        return np.zeros((len(tickers), max(days, 2)))

    matrix = np.array([
        eng.daily_returns(np.array(by_ticker.get(t, [0.0] * (min_len + 1)), dtype=np.float64)[-min_len:])
        for t in tickers
    ], dtype=np.float64)
    return matrix


@router.post("/risk", response_model=QuantResult)
async def portfolio_risk(body: PortfolioRiskInput) -> QuantResult:
    weights = np.array(body.weights, dtype=np.float64)
    returns_matrix = await _fetch_returns_matrix(body.tickers)

    # Weighted portfolio returns
    port_rets = weights @ returns_matrix

    bench_rows_matrix = await _fetch_returns_matrix(["SPY"], len(port_rets) + 1)
    bench_rets = bench_rows_matrix[0] if bench_rows_matrix.shape[0] > 0 else np.array([])

    corr = eng.correlation_matrix(returns_matrix).tolist()

    result = PortfolioRiskOutput(
        volatility_annualised=eng.volatility(port_rets),
        var_95=eng.var_historical(port_rets),
        cvar_95=eng.cvar_historical(port_rets),
        beta_to_spy=eng.beta(port_rets, bench_rets) if len(bench_rets) > 0 else None,
        sharpe=eng.sharpe_ratio(port_rets),
        sortino=eng.sortino_ratio(port_rets),
        max_drawdown=eng.max_drawdown(np.cumprod(1 + port_rets)),
        correlation_matrix=corr,
        as_of=datetime.date.today().isoformat(),
    )

    return QuantResult(
        data=result.model_dump(),
        sources=[f"supabase:prices_daily:{','.join(body.tickers)}"],
        as_of=datetime.date.today().isoformat(),
        warnings=[],
    )

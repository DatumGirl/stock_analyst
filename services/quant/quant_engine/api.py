"""FastAPI application for the quant engine service (port 8001)."""

import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from typing import Any, AsyncGenerator

import httpx
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from quant_engine import indicators, monte_carlo, returns, risk, valuation

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

_client: httpx.AsyncClient | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global _client
    _client = httpx.AsyncClient(timeout=30.0)
    yield
    await _client.aclose()


app = FastAPI(title="Quant Engine", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _api_ok(data: Any, sources: list[str], as_of: str, warnings: list[str] | None = None) -> dict[str, Any]:
    return {"data": data, "sources": sources, "as_of": as_of, "warnings": warnings or []}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _client_or_raise() -> httpx.AsyncClient:
    if _client is None:
        raise RuntimeError("HTTP client not initialised")
    return _client


async def _fetch_prices(ticker: str, limit: int = 252) -> list[dict[str, Any]]:
    """Fetch recent daily closes from Supabase."""
    resp = await _client_or_raise().get(
        f"{SUPABASE_URL}/rest/v1/prices_daily",
        params={"ticker": f"eq.{ticker}", "order": "date.desc", "limit": str(limit), "select": "date,close,volume"},
        headers={"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"},
    )
    if resp.status_code == 404 or resp.status_code == 200 and not resp.json():
        return []
    resp.raise_for_status()
    rows: list[dict[str, Any]] = resp.json()
    return list(reversed(rows))


# ─── Models ──────────────────────────────────────────────────────────────────

class RiskMetricsOut(BaseModel):
    volatility_30d: float | None
    beta: float | None
    max_drawdown: float | None
    var_95: float | None
    cvar_95: float | None
    sharpe: float | None
    sortino: float | None
    as_of: str


class PortfolioRiskIn(BaseModel):
    tickers: list[str]
    weights: list[float]


class ValuationIn(BaseModel):
    current_price: float
    eps: float | None = None
    fwd_eps: float | None = None
    revenue_per_share: float | None = None
    ebitda_per_share: float | None = None
    fcf_per_share: float | None = None
    growth_rate: float | None = None
    pe_low: float = 15.0
    pe_base: float = 22.0
    pe_high: float = 30.0


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/metrics/{ticker}")
async def get_metrics(ticker: str, period: str = "1Y") -> dict[str, Any]:
    limit_map = {"1M": 22, "3M": 66, "6M": 126, "1Y": 252, "3Y": 756}
    limit = limit_map.get(period.upper(), 252)

    rows = await _fetch_prices(ticker.upper(), limit)
    if len(rows) < 20:
        raise HTTPException(404, f"Insufficient price data for {ticker}")

    closes = np.array([float(r["close"]) for r in rows])
    rets = returns.log_returns(closes)

    metrics = RiskMetricsOut(
        volatility_30d=_nanf(risk.rolling_volatility(rets, 30)[-1]),
        beta=None,  # requires market returns — caller should provide
        max_drawdown=_nanf(risk.max_drawdown(closes)),
        var_95=_nanf(risk.var_historical(rets, 0.95)),
        cvar_95=_nanf(risk.cvar_historical(rets, 0.95)),
        sharpe=_nanf(risk.sharpe_ratio(rets)),
        sortino=_nanf(risk.sortino_ratio(rets)),
        as_of=rows[-1]["date"],
    )
    return _api_ok(metrics.model_dump(), [f"supabase/prices_daily/{ticker}"], _now())


@app.post("/portfolio/risk")
async def portfolio_risk(body: PortfolioRiskIn) -> dict[str, Any]:
    if len(body.tickers) != len(body.weights):
        raise HTTPException(400, "tickers and weights must be same length")

    all_rets: list[np.ndarray] = []
    warnings: list[str] = []
    for ticker in body.tickers:
        rows = await _fetch_prices(ticker.upper(), 252)
        if len(rows) < 20:
            warnings.append(f"Insufficient data for {ticker}")
            all_rets.append(np.zeros(252))
        else:
            closes = np.array([float(r["close"]) for r in rows])
            all_rets.append(returns.log_returns(closes))

    min_len = min(len(r) for r in all_rets)
    matrix = np.array([r[-min_len:] for r in all_rets])
    weights = np.array(body.weights)
    cov = np.cov(matrix) * 252

    port_vol = risk.portfolio_volatility(weights, cov)
    port_rets = (matrix.T @ weights)
    metrics = RiskMetricsOut(
        volatility_30d=_nanf(port_vol),
        beta=None,
        max_drawdown=_nanf(risk.max_drawdown(np.cumprod(1 + port_rets))),
        var_95=_nanf(risk.var_historical(port_rets)),
        cvar_95=_nanf(risk.cvar_historical(port_rets)),
        sharpe=_nanf(risk.sharpe_ratio(port_rets)),
        sortino=_nanf(risk.sortino_ratio(port_rets)),
        as_of=_now(),
    )
    return _api_ok(metrics.model_dump(), [f"supabase/prices_daily/{t}" for t in body.tickers], _now(), warnings)


@app.post("/valuation/{ticker}")
async def compute_valuation(ticker: str, body: ValuationIn) -> dict[str, Any]:
    results: list[valuation.ValuationResult] = []
    warnings: list[str] = []

    if body.eps and body.eps > 0:
        results.append(valuation.pe_valuation(body.eps, body.pe_low, body.pe_base, body.pe_high))
    else:
        warnings.append("EPS not provided — P/E valuation skipped")

    if body.fwd_eps and body.fwd_eps > 0:
        results.append(valuation.forward_pe_valuation(body.fwd_eps, body.pe_low, body.pe_base, body.pe_high))

    if body.eps and body.growth_rate and body.eps > 0 and body.growth_rate > 0:
        results.append(valuation.peg_valuation(body.eps, body.growth_rate))

    if body.revenue_per_share and body.revenue_per_share > 0:
        results.append(valuation.ps_valuation(body.revenue_per_share, 3.0, 5.0, 8.0))

    if body.fcf_per_share and body.fcf_per_share > 0:
        results.append(valuation.p_fcf_valuation(body.fcf_per_share, 15.0, 22.0, 30.0))
        if body.growth_rate:
            growth_rates = [body.growth_rate] * 5
            results.append(valuation.dcf_valuation(body.fcf_per_share, growth_rates))

    if not results:
        raise HTTPException(400, "No valid valuation inputs provided")

    agg = valuation.aggregate_valuation(results)
    output = [
        {
            "method": r.method,
            "low": r.low, "base": r.base, "high": r.high,
            "bear": r.bear, "bull": r.bull,
            "assumptions_version": r.assumptions_version,
            "source": "quant_engine",
            "as_of": _now(),
            "is_forecast": True,
        }
        for r in results
    ]
    output.append({
        "method": "aggregate",
        "low": agg["low"], "base": agg["base"], "high": agg["high"],
        "bear": agg["bear"], "bull": agg["bull"],
        "assumptions_version": "v1",
        "source": "quant_engine",
        "as_of": _now(),
        "is_forecast": True,
    })
    return _api_ok(output, ["quant_engine/valuation"], _now(), warnings)


@app.post("/snapshot/{portfolio_id}")
async def trigger_snapshot(portfolio_id: str) -> dict[str, Any]:
    # Background snapshot computation is handled by the portfolio-snapshot edge function.
    # This endpoint acknowledges the request; the edge function does the work.
    return _api_ok({"message": "snapshot queued", "portfolio_id": portfolio_id}, [], _now())


@app.post("/ingest/{ticker}")
async def ingest_ticker(ticker: str) -> dict[str, Any]:
    return _api_ok({"message": "ingestion queued", "ticker": ticker.upper()}, [], _now())


def _nanf(v: float) -> float | None:
    return None if (v is None or (isinstance(v, float) and np.isnan(v))) else float(v)

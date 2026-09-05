"""FastAPI application exposing the quant engine over HTTP.

Called by Supabase Edge Functions. Every endpoint is stateless;
inputs arrive as JSON, outputs are JSON. No database access here.
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, field_validator

from .indicators import atr, macd, rsi, sma, ema, support_resistance, vwap
from .monte_carlo import simulate_portfolio_cagr
from .returns import annualised_return, daily_returns, total_return
from .risk import (
    annualised_volatility,
    beta,
    conditional_var,
    correlation_matrix,
    max_drawdown,
    sharpe_ratio,
    sortino_ratio,
    value_at_risk,
)
from .valuation import (
    ValuationRange,
    dcf_range,
    ev_ebitda_range,
    forward_pe_range,
    pe_range,
    peer_implied_range,
    price_to_sales_range,
)

app = FastAPI(title="StockIntel Quant Engine", version="0.1.0")


# ─── request / response models ────────────────────────────────────────────────

class PriceSeriesRequest(BaseModel):
    prices: list[float]

    @field_validator("prices")
    @classmethod
    def at_least_two(cls, v: list[float]) -> list[float]:
        if len(v) < 2:
            raise ValueError("prices must contain at least 2 values")
        return v


class ReturnsRequest(BaseModel):
    prices: list[float]


class BetaRequest(BaseModel):
    asset_returns: list[float]
    benchmark_returns: list[float]


class VaRRequest(BaseModel):
    returns: list[float]
    confidence: float = 0.95


class SharpeRequest(BaseModel):
    returns: list[float]
    risk_free_rate: float = 0.0


class CorrelationRequest(BaseModel):
    returns_by_ticker: dict[str, list[float]]


class RSIRequest(BaseModel):
    prices: list[float]
    period: int = 14


class MACDRequest(BaseModel):
    prices: list[float]
    fast: int = 12
    slow: int = 26
    signal: int = 9


class ATRRequest(BaseModel):
    highs: list[float]
    lows: list[float]
    closes: list[float]
    period: int = 14


class VWAPRequest(BaseModel):
    highs: list[float]
    lows: list[float]
    closes: list[float]
    volumes: list[int]


class PERangeRequest(BaseModel):
    eps: float
    pe_low: float
    pe_base: float
    pe_high: float


class FwdPERangeRequest(BaseModel):
    fwd_eps: float
    pe_low: float
    pe_base: float
    pe_high: float


class DCFRequest(BaseModel):
    free_cash_flows: list[float]
    terminal_growth_rates: tuple[float, float, float]
    discount_rates: tuple[float, float, float]
    shares: int
    net_debt: float = 0.0


class EVEBITDARequest(BaseModel):
    ebitda: float
    net_debt: float
    shares: int
    multiple_low: float
    multiple_base: float
    multiple_high: float


class PSRangeRequest(BaseModel):
    revenue_per_share: float
    ps_low: float
    ps_base: float
    ps_high: float


class PeerRangeRequest(BaseModel):
    metric_value: float
    peer_multiples: list[float]


class MonteCarloRequest(BaseModel):
    annual_mean_return: float
    annual_volatility: float
    horizon_years: int
    target_cagr: float
    n_paths: int = 10_000
    seed: int = 42


# ─── returns endpoints ────────────────────────────────────────────────────────

@app.post("/returns/daily")
def compute_daily_returns(req: ReturnsRequest) -> dict:
    try:
        return {"returns": daily_returns(req.prices)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/returns/total")
def compute_total_return(req: ReturnsRequest) -> dict:
    try:
        return {"total_return": total_return(req.prices)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/returns/annualised")
def compute_annualised_return(req: ReturnsRequest) -> dict:
    try:
        return {"annualised_return": annualised_return(req.prices)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── risk endpoints ───────────────────────────────────────────────────────────

@app.post("/risk/volatility")
def compute_volatility(req: ReturnsRequest) -> dict:
    try:
        return {"annualised_volatility": annualised_volatility(req.prices)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/risk/beta")
def compute_beta(req: BetaRequest) -> dict:
    try:
        return {"beta": beta(req.asset_returns, req.benchmark_returns)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/risk/drawdown")
def compute_drawdown(req: ReturnsRequest) -> dict:
    try:
        return {"max_drawdown": max_drawdown(req.prices)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/risk/var")
def compute_var(req: VaRRequest) -> dict:
    try:
        return {
            "var": value_at_risk(req.returns, req.confidence),
            "cvar": conditional_var(req.returns, req.confidence),
            "confidence": req.confidence,
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/risk/sharpe")
def compute_sharpe(req: SharpeRequest) -> dict:
    try:
        return {
            "sharpe": sharpe_ratio(req.returns, req.risk_free_rate),
            "sortino": sortino_ratio(req.returns, req.risk_free_rate),
        }
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/risk/correlation")
def compute_correlation(req: CorrelationRequest) -> dict:
    try:
        return {"correlation": correlation_matrix(req.returns_by_ticker)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── indicator endpoints ──────────────────────────────────────────────────────

@app.post("/indicators/rsi")
def compute_rsi(req: RSIRequest) -> dict:
    try:
        return {"rsi": rsi(req.prices, req.period)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/indicators/macd")
def compute_macd(req: MACDRequest) -> dict:
    try:
        return macd(req.prices, req.fast, req.slow, req.signal)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/indicators/atr")
def compute_atr(req: ATRRequest) -> dict:
    try:
        return {"atr": atr(req.highs, req.lows, req.closes, req.period)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/indicators/vwap")
def compute_vwap(req: VWAPRequest) -> dict:
    try:
        return {"vwap": vwap(req.highs, req.lows, req.closes, req.volumes)}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/indicators/support-resistance")
def compute_support_resistance(req: RSIRequest) -> dict:
    try:
        return support_resistance(req.prices, req.period)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── valuation endpoints ──────────────────────────────────────────────────────

def _val_response(r: ValuationRange) -> dict:
    return r.to_dict()


@app.post("/valuation/pe")
def compute_pe(req: PERangeRequest) -> dict:
    try:
        return _val_response(pe_range(req.eps, req.pe_low, req.pe_base, req.pe_high))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/valuation/fwd-pe")
def compute_fwd_pe(req: FwdPERangeRequest) -> dict:
    try:
        return _val_response(forward_pe_range(req.fwd_eps, req.pe_low, req.pe_base, req.pe_high))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/valuation/dcf")
def compute_dcf(req: DCFRequest) -> dict:
    try:
        return _val_response(
            dcf_range(
                req.free_cash_flows,
                req.terminal_growth_rates,
                req.discount_rates,
                req.shares,
                req.net_debt,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/valuation/ev-ebitda")
def compute_ev_ebitda(req: EVEBITDARequest) -> dict:
    try:
        return _val_response(
            ev_ebitda_range(
                req.ebitda, req.net_debt, req.shares,
                req.multiple_low, req.multiple_base, req.multiple_high,
            )
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/valuation/ps")
def compute_ps(req: PSRangeRequest) -> dict:
    try:
        return _val_response(
            price_to_sales_range(req.revenue_per_share, req.ps_low, req.ps_base, req.ps_high)
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@app.post("/valuation/peers")
def compute_peers(req: PeerRangeRequest) -> dict:
    try:
        return _val_response(peer_implied_range(req.metric_value, req.peer_multiples))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─── monte carlo ──────────────────────────────────────────────────────────────

@app.post("/monte-carlo/portfolio-cagr")
def compute_monte_carlo(req: MonteCarloRequest) -> dict:
    try:
        result = simulate_portfolio_cagr(
            req.annual_mean_return,
            req.annual_volatility,
            req.horizon_years,
            req.target_cagr,
            req.n_paths,
            req.seed,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

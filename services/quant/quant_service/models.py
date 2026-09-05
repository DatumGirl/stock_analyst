"""Request / response models for the quant service API."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, field_validator


# ─── Shared envelope ─────────────────────────────────────────────────────────

class QuantResult(BaseModel):
    data: Any
    sources: list[str]
    as_of: str
    warnings: list[str]


# ─── Metrics ─────────────────────────────────────────────────────────────────

class ReturnMetrics(BaseModel):
    ticker: str
    period: str
    total_return: float
    annualised_return: float
    volatility_30d: float
    volatility_252d: float
    beta: float | None
    sharpe: float | None
    sortino: float | None
    max_drawdown: float
    var_95: float
    cvar_95: float
    as_of: str


# ─── Valuation ───────────────────────────────────────────────────────────────

class ValuationInput(BaseModel):
    ticker: str
    current_price: Decimal
    eps_ttm: Decimal | None = None
    eps_fwd: Decimal | None = None
    revenue_ttm: Decimal | None = None
    revenue_fwd: Decimal | None = None
    ebitda_ttm: Decimal | None = None
    fcf_ttm: Decimal | None = None
    shares_outstanding: Decimal | None = None
    net_debt: Decimal | None = None
    # DCF inputs
    fcf_growth_rate: float | None = None
    terminal_growth_rate: float | None = None
    discount_rate: float | None = None
    # Peer inputs (list of (pe, growth) tuples)
    peer_multiples: list[tuple[float, float]] | None = None


class ValuationOutput(BaseModel):
    ticker: str
    method: str
    low: Decimal
    base: Decimal
    high: Decimal
    bear: Decimal
    bull: Decimal
    current_price: Decimal
    gap_pct: float          # (base - current) / current
    assumptions_version: str
    is_forecast: bool = True


# ─── Portfolio risk ───────────────────────────────────────────────────────────

class PortfolioRiskInput(BaseModel):
    tickers: list[str]
    weights: list[float]

    @field_validator("weights")
    @classmethod
    def weights_sum_to_one(cls, v: list[float]) -> list[float]:
        total = sum(v)
        if not (0.99 <= total <= 1.01):
            raise ValueError(f"Weights must sum to 1.0, got {total:.4f}")
        return v


class PortfolioRiskOutput(BaseModel):
    volatility_annualised: float
    var_95: float
    cvar_95: float
    beta_to_spy: float | None
    sharpe: float | None
    sortino: float | None
    max_drawdown: float
    correlation_matrix: list[list[float]]
    as_of: str
    is_forecast: bool = False

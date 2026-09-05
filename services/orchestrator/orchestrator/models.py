"""Orchestrator request / response models."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel


class AgentResult(BaseModel):
    """Contract every agent must satisfy."""
    data: Any
    sources: list[str]
    as_of: str
    warnings: list[str]


# ─── Analyze ─────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    ticker: str
    portfolio_id: str | None = None


class SignalDirection(BaseModel):
    fundamentals: Literal["positive", "neutral", "negative"]
    valuation: Literal["positive", "neutral", "negative"]
    momentum: Literal["positive", "neutral", "negative"]


class AnalyzeResponse(BaseModel):
    ticker: str
    run_id: str
    verdict: str
    signals: SignalDirection
    valuation_range: dict[str, Any] | None
    action: Literal["Watch", "Hold", "Research", "Avoid"]
    portfolio_fit: str | None
    full_report_markdown: str
    model_disagreements: list[str]
    data_freshness: str
    as_of: str
    is_forecast: bool = True


# ─── Compare ─────────────────────────────────────────────────────────────────

class CompareRequest(BaseModel):
    tickers: list[str]


class CompareRow(BaseModel):
    ticker: str
    revenue_growth: float | None
    pe: str | None
    fwd_pe: str | None
    gross_margin: float | None
    roic: float | None
    debt_to_equity: float | None
    momentum_score: float | None
    fair_value_gap_pct: float | None


class CompareResponse(BaseModel):
    tickers: list[str]
    chief_analyst_summary: str
    rows: list[CompareRow]
    as_of: str
    is_forecast: bool = True


# ─── Brief ───────────────────────────────────────────────────────────────────

class OpportunityCard(BaseModel):
    ticker: str
    score: int
    one_line_thesis: str
    action: Literal["Watch", "Hold", "Research", "Avoid"]


class ActionItem(BaseModel):
    ticker: str
    action: Literal["Watch", "Hold", "Research", "Avoid"]
    reason: str


class BriefResponse(BaseModel):
    date: str
    portfolio_return: float
    health_score: int
    risk_level: Literal["low", "moderate", "elevated", "high"]
    target_probability: float
    target_probability_delta: float
    important: list[dict[str, Any]]
    catalysts: list[dict[str, Any]]
    opportunities: list[OpportunityCard]
    action_plan: list[ActionItem]
    rebalance_required: bool
    as_of: str

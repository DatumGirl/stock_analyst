"""POST /analyze — run the Chief Analyst pipeline for a single ticker."""
from __future__ import annotations

import asyncio
import datetime
import logging
import traceback
from typing import Any

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..agents.fundamental import FundamentalAgent
from ..agents.graph import GraphAgent
from ..agents.news import NewsAgent
from ..agents.portfolio import PortfolioAgent
from ..agents.technical import TechnicalAgent
from ..chief_analyst import ChiefAnalyst
from ..config import settings
from ..models import AgentResult, AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])
logger = logging.getLogger(__name__)

# Preference order when multiple valuation methods are available
_VALUATION_METHOD_PRIORITY = ["dcf", "ev_ebitda", "fwd_pe", "pe", "ps"]


async def _fetch_valuation(
    ticker: str,
    fundamental: AgentResult,
    technical: AgentResult,
) -> dict[str, Any] | None:
    """POST to /valuation/{ticker} on the quant service; return the best result."""
    # Current price from the technical agent's recent price snapshot
    recent = technical.data.get("recent_prices", [])
    current_price = recent[0].get("close") if recent else None
    if not current_price:
        return None

    # Annualise quarterly values by summing up to 4 periods (TTM)
    latest = fundamental.data.get("latest_period") or {}
    prior = fundamental.data.get("prior_periods", [])
    all_periods = [latest] + list(prior)

    def ttm(key: str) -> float | None:
        vals = [p[key] for p in all_periods[:4] if p.get(key) is not None]
        return round(sum(vals), 4) if vals else None

    payload: dict[str, Any] = {"ticker": ticker, "current_price": current_price}
    for key, fn_key in [("eps_ttm", "eps"), ("revenue_ttm", "revenue"), ("fcf_ttm", "fcf")]:
        v = ttm(fn_key)
        if v is not None:
            payload[key] = v

    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{settings.quant_service_url}/valuation/{ticker}",
                json=payload,
                timeout=10.0,
            )
        if res.status_code != 200:
            return None
        rows: list[dict[str, Any]] = res.json().get("data", [])
    except Exception as exc:
        logger.debug("Valuation fetch skipped for %s: %s", ticker, exc)
        return None

    if not rows:
        return None

    by_method = {r["method"]: r for r in rows}
    for method in _VALUATION_METHOD_PRIORITY:
        if method in by_method:
            return by_method[method]
    return rows[0]


def _build_agents() -> tuple[FundamentalAgent, TechnicalAgent, NewsAgent, GraphAgent, PortfolioAgent]:
    kwargs = dict(
        supabase_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
    )
    return (
        FundamentalAgent(**kwargs),
        TechnicalAgent(quant_service_url=settings.quant_service_url, **kwargs),
        NewsAgent(**kwargs),
        GraphAgent(graph_service_url=settings.graph_service_url, **kwargs),
        PortfolioAgent(quant_service_url=settings.quant_service_url, **kwargs),
    )


@router.post("/analyze", response_model=dict)
async def analyze_ticker(body: AnalyzeRequest) -> JSONResponse:
    ticker = body.ticker.upper()
    try:
        fundamental_agent, technical_agent, news_agent, graph_agent, portfolio_agent = _build_agents()

        # Run independent agents in parallel
        fundamental, technical, news, graph = await asyncio.gather(
            fundamental_agent.run(ticker=ticker),
            technical_agent.run(ticker=ticker),
            news_agent.run(ticker=ticker),
            graph_agent.run(ticker=ticker),
        )

        portfolio = None
        if body.portfolio_id:
            portfolio = await portfolio_agent.run(
                portfolio_id=body.portfolio_id,
                candidate_ticker=ticker,
            )

        analyst = ChiefAnalyst()

        valuation_range = await _fetch_valuation(ticker, fundamental, technical)

        if not settings.anthropic_api_key:
            return JSONResponse({
                "data": {
                    "ticker": ticker,
                    "run_id": "dev-stub",
                    "verdict": f"Development mode — analysis for {ticker} (no Anthropic key configured)",
                    "signals": {"fundamentals": "neutral", "valuation": "neutral", "momentum": "neutral"},
                    "valuation_range": valuation_range,
                    "action": "Research",
                    "portfolio_fit": None,
                    "full_report_markdown": f"# {ticker} Analysis\n\nDevelopment stub — configure ANTHROPIC_API_KEY to enable live analysis.",
                    "model_disagreements": [],
                    "data_freshness": f"as of {datetime.date.today()}",
                    "as_of": datetime.date.today().isoformat(),
                    "is_forecast": True,
                },
                "sources": fundamental.sources + technical.sources + news.sources,
                "as_of": datetime.date.today().isoformat(),
                "warnings": fundamental.warnings + technical.warnings + news.warnings,
            })

        result: AnalyzeResponse = await analyst.analyze(
            ticker=ticker,
            fundamental=fundamental,
            technical=technical,
            news=news,
            graph=graph,
            portfolio=portfolio,
        )

        if valuation_range is not None:
            result = result.model_copy(update={"valuation_range": valuation_range})

        all_warnings = fundamental.warnings + technical.warnings + news.warnings + graph.warnings
        all_sources = fundamental.sources + technical.sources + news.sources + graph.sources

        return JSONResponse({
            "data": result.model_dump(),
            "sources": all_sources,
            "as_of": result.as_of,
            "warnings": all_warnings,
        })

    except BaseException as exc:
        # Catch BaseException (including asyncio.CancelledError) so Railway
        # always gets a proper JSON response instead of an empty 500.
        logger.error("analyze_ticker failed for %s: %s", ticker, traceback.format_exc())
        return JSONResponse(
            {"detail": f"Analysis failed: {type(exc).__name__}: {exc}"},
            status_code=500,
        )

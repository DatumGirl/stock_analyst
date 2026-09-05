"""POST /analyze — run the Chief Analyst pipeline for a single ticker."""
from __future__ import annotations

import asyncio
import datetime
import logging
import traceback

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from ..agents.fundamental import FundamentalAgent
from ..agents.graph import GraphAgent
from ..agents.news import NewsAgent
from ..agents.portfolio import PortfolioAgent
from ..agents.technical import TechnicalAgent
from ..chief_analyst import ChiefAnalyst
from ..config import settings
from ..models import AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["analyze"])
logger = logging.getLogger(__name__)


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

        if not settings.anthropic_api_key:
            return JSONResponse({
                "data": {
                    "ticker": ticker,
                    "run_id": "dev-stub",
                    "verdict": f"Development mode — analysis for {ticker} (no Anthropic key configured)",
                    "signals": {"fundamentals": "neutral", "valuation": "neutral", "momentum": "neutral"},
                    "valuation_range": None,
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

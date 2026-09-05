"""POST /compare — compare up to 4 tickers side-by-side."""
from __future__ import annotations

import asyncio
import datetime

from fastapi import APIRouter, HTTPException

from ..agents.fundamental import FundamentalAgent
from ..agents.technical import TechnicalAgent
from ..chief_analyst import ChiefAnalyst
from ..config import settings
from ..models import CompareRequest, CompareResponse, CompareRow

router = APIRouter(tags=["compare"])


@router.post("/compare", response_model=dict)
async def compare_tickers(body: CompareRequest) -> dict:
    if len(body.tickers) < 2:
        raise HTTPException(status_code=422, detail="At least 2 tickers required")
    if len(body.tickers) > settings.max_compare_tickers:
        raise HTTPException(
            status_code=422,
            detail=f"Maximum {settings.max_compare_tickers} tickers per comparison",
        )

    tickers = [t.upper() for t in body.tickers]
    kwargs = dict(
        supabase_url=settings.supabase_url,
        service_role_key=settings.supabase_service_role_key,
    )
    fund_agent = FundamentalAgent(**kwargs)
    tech_agent = TechnicalAgent(quant_service_url=settings.quant_service_url, **kwargs)

    # Fetch data for all tickers in parallel
    fund_results, tech_results = await asyncio.gather(
        asyncio.gather(*[fund_agent.run(ticker=t) for t in tickers]),
        asyncio.gather(*[tech_agent.run(ticker=t) for t in tickers]),
    )

    rows: list[CompareRow] = []
    raw_rows: list[dict] = []

    for i, ticker in enumerate(tickers):
        fund = fund_results[i].data
        tech = tech_results[i].data
        latest = fund.get("latest_period") or {}
        metrics = tech.get("metrics") or {}

        row = CompareRow(
            ticker=ticker,
            revenue_growth=latest.get("revenue_growth"),
            pe=None,
            fwd_pe=None,
            gross_margin=latest.get("gross_margin"),
            roic=None,
            debt_to_equity=None,
            momentum_score=None,
            fair_value_gap_pct=None,
        )
        rows.append(row)
        raw_rows.append(row.model_dump())

    today = datetime.date.today().isoformat()
    analyst = ChiefAnalyst()

    if not settings.anthropic_api_key:
        summary = f"Development mode — comparison of {', '.join(tickers)} (no Anthropic key configured)"
    else:
        summary = await analyst.compare(tickers, raw_rows)

    result = CompareResponse(
        tickers=tickers,
        chief_analyst_summary=summary,
        rows=rows,
        as_of=today,
        is_forecast=True,
    )

    all_warnings = [w for r in list(fund_results) + list(tech_results) for w in r.warnings]

    return {
        "data": result.model_dump(),
        "sources": [f"supabase:fundamentals:{t}" for t in tickers],
        "as_of": today,
        "warnings": all_warnings,
    }

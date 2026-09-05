"""GET /brief/{portfolio_id} — daily portfolio brief.

On first request of the day the route automatically runs the data pipeline:
  1. Ingest fresh prices, fundamentals, and news for all portfolio tickers.
  2. Compute technical composite signals for each ticker.
  3. Compute and persist today's portfolio snapshot.

Subsequent calls within the same day skip the pipeline and return cached data.
"""
from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

import httpx
from fastapi import APIRouter, Query

from ..config import settings
from ..models import ActionItem, BriefResponse, OpportunityCard

router = APIRouter(tags=["brief"])
logger = logging.getLogger(__name__)


# ─── Supabase helper ──────────────────────────────────────────────────────────

async def _supabase_get(path: str, params: dict[str, str]) -> list[dict[str, Any]]:
    if not settings.supabase_url:
        return []
    url = f"{settings.supabase_url}/rest/v1/{path}"
    headers = {
        "apikey": settings.supabase_service_role_key,
        "Authorization": f"Bearer {settings.supabase_service_role_key}",
    }
    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=headers, params=params, timeout=10.0)
    return res.json() if res.status_code == 200 else []


# ─── Quant service helpers ────────────────────────────────────────────────────

async def _quant_post(path: str, timeout: float = 30.0) -> dict[str, Any] | None:
    """POST to the quant service; swallow errors so the brief is never blocked."""
    if not settings.quant_service_url:
        return None
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{settings.quant_service_url}{path}",
                timeout=timeout,
            )
        return res.json() if res.status_code == 200 else None
    except Exception as exc:
        logger.debug("Quant POST %s failed: %s", path, exc)
        return None


# ─── Auto-pipeline ────────────────────────────────────────────────────────────

async def _ensure_pipeline(portfolio_id: str, tickers: list[str], today: str) -> None:
    """Run ingest → signals → snapshot if today's snapshot does not yet exist."""
    if not tickers:
        return

    # Skip if a fresh snapshot was already computed today
    snapshots = await _supabase_get(
        "portfolio_snapshots",
        {
            "portfolio_id": f"eq.{portfolio_id}",
            "date": f"eq.{today}",
            "select": "date",
            "limit": "1",
        },
    )
    if snapshots:
        return

    logger.info("Running data pipeline for portfolio %s (%d tickers)", portfolio_id, len(tickers))

    # 1. Ingest: pull 2 years of prices + fundamentals + news from yfinance
    await asyncio.gather(
        *[_quant_post(f"/ingest/{t}", timeout=45.0) for t in tickers],
        return_exceptions=True,
    )

    # 2. Signals: compute technical composite score for each ticker
    await asyncio.gather(
        *[_quant_post(f"/signals/{t}", timeout=15.0) for t in tickers],
        return_exceptions=True,
    )

    # 3. Snapshot: compute and persist today's portfolio snapshot
    await _quant_post(f"/snapshot/{portfolio_id}", timeout=20.0)


# ─── Opportunity thesis ────────────────────────────────────────────────────────

def _thesis(signal: dict[str, Any]) -> str:
    """One-line thesis derived from the signal score — no LLM calls."""
    score = int(signal.get("rank_score", 50))
    if score >= 75:
        return "Strong technical momentum — RSI and trend both constructive"
    if score >= 60:
        return "Moderate upside signal — trend and momentum aligned"
    if score >= 40:
        return "Mixed signals — monitor for confirmation before adding"
    return "Weak technical setup — caution warranted near-term"


# ─── Route ───────────────────────────────────────────────────────────────────

@router.get("/brief/{portfolio_id}", response_model=dict)
async def daily_brief(
    portfolio_id: str,
    date: str = Query(default=None, description="YYYY-MM-DD, defaults to today"),
) -> dict:
    today = date or datetime.date.today().isoformat()

    # Fetch positions first (needed for pipeline + signals query)
    positions = await _supabase_get(
        "positions",
        {"portfolio_id": f"eq.{portfolio_id}", "select": "ticker"},
    )
    tickers = list({p["ticker"] for p in positions})

    # Run pipeline if today's data is missing
    await _ensure_pipeline(portfolio_id, tickers, today)

    # Fetch latest two snapshots (for delta calculation)
    snapshots = await _supabase_get(
        "portfolio_snapshots",
        {
            "portfolio_id": f"eq.{portfolio_id}",
            "order": "date.desc",
            "limit": "2",
            "select": "*",
        },
    )
    snapshot = snapshots[0] if snapshots else None
    prev_snapshot = snapshots[1] if len(snapshots) > 1 else None

    # Material changes today
    changes = await _supabase_get(
        "portfolio_changes",
        {
            "portfolio_id": f"eq.{portfolio_id}",
            "date": f"eq.{today}",
            "order": "created_at.desc",
            "select": "*",
        },
    )

    # Upcoming catalysts
    catalysts = await _supabase_get(
        "catalysts",
        {
            "date": f"gte.{today}",
            "order": "date.asc",
            "limit": "5",
            "select": "*",
        },
    )

    # ML / technical signals for today
    signals_rows: list[dict[str, Any]] = []
    if tickers:
        tickers_param = ",".join(f"'{t}'" for t in tickers[:10])
        signals_rows = await _supabase_get(
            "signals",
            {
                "ticker": f"in.({tickers_param})",
                "date": f"eq.{today}",
                "order": "rank_score.desc",
                "select": "*",
            },
        )

    # Build opportunities with a real one-line thesis
    opportunities = [
        OpportunityCard(
            ticker=s["ticker"],
            score=int(s.get("rank_score", 50)),
            one_line_thesis=_thesis(s),
            action=(
                "Watch" if s.get("rank_score", 0) >= 75
                else "Hold" if s.get("rank_score", 0) >= 50
                else "Research"
            ),
        )
        for s in signals_rows[:5]
    ]

    # Action plan
    action_plan = [
        ActionItem(
            ticker=s["ticker"],
            action=(
                "Watch" if s.get("rank_score", 0) >= 75
                else "Hold" if s.get("rank_score", 0) >= 50
                else "Research"
            ),
            reason=_thesis(s),
        )
        for s in signals_rows[:8]
    ]

    # Snapshot values
    health_score = int(snapshot.get("health_score", 75)) if snapshot else 75
    day_return = float(snapshot.get("day_return", 0.0)) if snapshot else 0.0
    target_probability = float(snapshot.get("target_probability", 0.5)) if snapshot else 0.5
    prev_probability = (
        float(prev_snapshot.get("target_probability", target_probability))
        if prev_snapshot else target_probability
    )

    # Rebalance flag: concentration > 40% in any one sector warrants review
    exposures: dict[str, float] = snapshot.get("exposures", {}) if snapshot else {}
    rebalance_required = any(v > 0.40 for v in exposures.values())

    result = BriefResponse(
        date=today,
        portfolio_return=day_return,
        health_score=health_score,
        risk_level=snapshot.get("risk_level", "moderate") if snapshot else "moderate",
        target_probability=target_probability,
        target_probability_delta=target_probability - prev_probability,
        important=changes[:3],
        catalysts=catalysts[:5],
        opportunities=opportunities,
        action_plan=action_plan,
        rebalance_required=rebalance_required,
        as_of=snapshot.get("created_at", today) if snapshot else today,
    )

    warnings: list[str] = []
    if not snapshot:
        warnings.append(f"No snapshot computed for {portfolio_id} — pipeline may need Supabase + quant service")

    return {
        "data": result.model_dump(),
        "sources": [f"supabase:portfolio_snapshots:{portfolio_id}"],
        "as_of": result.as_of,
        "warnings": warnings,
    }

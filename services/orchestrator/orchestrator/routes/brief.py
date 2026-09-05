"""GET /brief/{portfolio_id} — daily portfolio brief."""
from __future__ import annotations

import datetime
from typing import Any

import httpx
from fastapi import APIRouter, Query

from ..config import settings
from ..models import ActionItem, BriefResponse, OpportunityCard

router = APIRouter(tags=["brief"])


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


@router.get("/brief/{portfolio_id}", response_model=dict)
async def daily_brief(
    portfolio_id: str,
    date: str = Query(default=None, description="YYYY-MM-DD, defaults to today"),
) -> dict:
    today = date or datetime.date.today().isoformat()

    # Fetch latest snapshot
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

    # ML signals for current positions
    positions = await _supabase_get(
        "positions",
        {"portfolio_id": f"eq.{portfolio_id}", "select": "ticker"},
    )
    tickers = list({p["ticker"] for p in positions})

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

    # Build opportunities from ML signals
    opportunities = [
        OpportunityCard(
            ticker=s["ticker"],
            score=int(s.get("rank_score", 50)),
            one_line_thesis=f"ML rank {int(s.get('rank_score', 50))}/100 — see full analysis",
            action="Research",
        )
        for s in signals_rows[:5]
    ] if signals_rows else []

    # Action plan (Watch = high score, Hold = medium, Research = catalyst tomorrow, Avoid = low)
    action_plan = [
        ActionItem(
            ticker=s["ticker"],
            action="Watch" if s.get("rank_score", 0) >= 75 else "Hold" if s.get("rank_score", 0) >= 50 else "Research",
            reason=f"ML rank {int(s.get('rank_score', 50))}/100",
        )
        for s in signals_rows[:8]
    ]

    # Snapshot values
    health_score = int(snapshot.get("health_score", 75)) if snapshot else 75
    day_return = float(snapshot.get("day_return", 0.0)) if snapshot else 0.0
    target_probability = float(snapshot.get("target_probability", 0.5)) if snapshot else 0.5
    prev_probability = float(prev_snapshot.get("target_probability", target_probability)) if prev_snapshot else target_probability

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
        rebalance_required=False,
        as_of=snapshot.get("created_at", today) if snapshot else today,
    )

    warnings: list[str] = []
    if not snapshot:
        warnings.append(f"No portfolio snapshot found for {portfolio_id} — run portfolio-snapshot job")

    return {
        "data": result.model_dump(),
        "sources": [f"supabase:portfolio_snapshots:{portfolio_id}"],
        "as_of": result.as_of,
        "warnings": warnings,
    }

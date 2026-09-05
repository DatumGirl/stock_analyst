"""Macro agent: market regime, rates, sector, economic calendar."""
from __future__ import annotations

import datetime
from typing import Any

from .base import BaseAgent
from ..models import AgentResult


class MacroAgent(BaseAgent):
    async def run(self, date: str | None = None) -> AgentResult:  # type: ignore[override]
        today = date or datetime.date.today().isoformat()
        warnings: list[str] = []

        # Fetch macro events from Supabase
        macro_events = await self._supabase_get(
            "news_events",
            {
                "tickers": "is.null",
                "as_of": f"gte.{(datetime.date.today() - datetime.timedelta(days=3)).isoformat()}",
                "order": "materiality_score.desc",
                "limit": "10",
                "select": "*",
            },
        )

        if not macro_events:
            warnings.append("No macro events found — macro context will be limited")

        return AgentResult(
            data={
                "date": today,
                "macro_events": macro_events,
                "regime": "unknown",   # populated by a data provider in production
            },
            sources=["supabase:news_events:macro"],
            as_of=today,
            warnings=warnings,
        )

"""News agent: events, filings, analyst revisions, materiality chain."""
from __future__ import annotations

import datetime
from typing import Any

from .base import BaseAgent
from ..models import AgentResult

# Materiality threshold — events below this score are filtered out
MIN_MATERIALITY = 0.3


class NewsAgent(BaseAgent):
    async def run(self, ticker: str, days: int = 7) -> AgentResult:  # type: ignore[override]
        today = datetime.date.today()
        cutoff = (today - datetime.timedelta(days=days)).isoformat()
        warnings: list[str] = []

        events = await self._supabase_get(
            "news_events",
            {
                "or": f"(tickers.cs.{{{ticker}}})",
                "as_of": f"gte.{cutoff}",
                "order": "materiality_score.desc",
                "limit": "20",
                "select": "*",
            },
        )

        catalysts = await self._supabase_get(
            "catalysts",
            {
                "ticker": f"eq.{ticker}",
                "date": f"gte.{today.isoformat()}",
                "order": "date.asc",
                "limit": "5",
                "select": "*",
            },
        )

        material = [e for e in events if e.get("materiality_score", 0) >= MIN_MATERIALITY]
        filtered_count = len(events) - len(material)
        if filtered_count > 0:
            warnings.append(f"{filtered_count} low-materiality events filtered out")
        if not material and not catalysts:
            warnings.append(f"No material news found for {ticker} in the last {days} days")

        return AgentResult(
            data={"ticker": ticker, "news_events": material, "catalysts": catalysts},
            sources=[f"supabase:news_events:{ticker}", f"supabase:catalysts:{ticker}"],
            as_of=today.isoformat(),
            warnings=warnings,
        )

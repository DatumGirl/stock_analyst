"""Fundamental agent: financial statements, earnings, valuation multiples."""
from __future__ import annotations

import datetime
from typing import Any

from .base import BaseAgent
from ..models import AgentResult


class FundamentalAgent(BaseAgent):
    """Fetch and structure fundamental data for a ticker.

    Returns earnings, margins, growth, and balance-sheet quality.
    Never interprets, ranks by attractiveness, or recommends.
    """

    async def run(self, ticker: str) -> AgentResult:  # type: ignore[override]
        today = datetime.date.today().isoformat()
        warnings: list[str] = []

        fundamentals = await self._supabase_get(
            "fundamentals",
            {
                "ticker": f"eq.{ticker}",
                "order": "as_of.desc",
                "limit": "4",
                "select": "*",
            },
        )

        estimates = await self._supabase_get(
            "estimates",
            {
                "ticker": f"eq.{ticker}",
                "order": "as_of.desc",
                "limit": "2",
                "select": "*",
            },
        )

        if not fundamentals:
            warnings.append(f"No fundamentals data found for {ticker}")

        data: dict[str, Any] = {
            "ticker": ticker,
            "latest_period": fundamentals[0] if fundamentals else None,
            "prior_periods": fundamentals[1:] if len(fundamentals) > 1 else [],
            "estimates": estimates,
        }

        sources = []
        if fundamentals:
            sources.append(f"supabase:fundamentals:{ticker}:{fundamentals[0].get('source', 'unknown')}")
        if estimates:
            sources.append(f"supabase:estimates:{ticker}")

        as_of = fundamentals[0].get("as_of", today) if fundamentals else today

        return AgentResult(data=data, sources=sources, as_of=as_of, warnings=warnings)

"""News Agent — fetches news, catalysts and runs them through the materiality chain."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel


class MaterialNewsItem(BaseModel):
    id: str
    headline: str
    url: str | None
    source: str
    tickers: list[str]
    sentiment: str
    materiality_score: float
    affects_earnings: bool
    affects_valuation: bool
    affects_thesis: bool
    as_of: str


class NewsData(BaseModel):
    ticker: str
    material_news: list[MaterialNewsItem]
    upcoming_catalysts: list[dict[str, Any]]
    as_of: str
    warnings: list[str]


class AgentResult(BaseModel):
    data: NewsData
    sources: list[str]
    as_of: str
    warnings: list[str]


class NewsAgent:
    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        self._url = supabase_url
        self._key = supabase_key

    def _headers(self) -> dict[str, str]:
        return {"apikey": self._key, "Authorization": f"Bearer {self._key}"}

    async def run(self, ticker: str, client: httpx.AsyncClient) -> AgentResult:
        warnings: list[str] = []
        now = datetime.now(timezone.utc).isoformat()
        today = datetime.now(timezone.utc).date().isoformat()

        # News events containing this ticker (Supabase array containment)
        news_resp = await client.get(
            f"{self._url}/rest/v1/news_events",
            params={
                "tickers": f"cs.{{\"{ticker}\"}}",
                "order": "as_of.desc",
                "limit": "20",
                "materiality_score": "gte.0.5",
            },
            headers=self._headers(),
        )
        news_rows: list[dict[str, Any]] = []
        if news_resp.status_code == 200:
            news_rows = news_resp.json()
        else:
            warnings.append(f"News fetch failed: HTTP {news_resp.status_code}")

        # Upcoming catalysts
        cat_resp = await client.get(
            f"{self._url}/rest/v1/catalysts",
            params={
                "ticker": f"eq.{ticker}",
                "date": f"gte.{today}",
                "order": "date.asc",
                "limit": "10",
            },
            headers=self._headers(),
        )
        catalysts: list[dict[str, Any]] = []
        if cat_resp.status_code == 200:
            catalysts = cat_resp.json()

        material_news = [
            MaterialNewsItem(
                id=row.get("id", ""),
                headline=row.get("headline", ""),
                url=row.get("url"),
                source=row.get("source", ""),
                tickers=row.get("tickers", []),
                sentiment=row.get("sentiment", "neutral"),
                materiality_score=float(row.get("materiality_score", 0)),
                affects_earnings=bool(row.get("affects_earnings", False)),
                affects_valuation=bool(row.get("affects_valuation", False)),
                affects_thesis=bool(row.get("affects_thesis", False)),
                as_of=row.get("as_of", now),
            )
            for row in news_rows[:5]  # max 5 material items
        ]

        data = NewsData(
            ticker=ticker,
            material_news=material_news,
            upcoming_catalysts=catalysts,
            as_of=now,
            warnings=warnings,
        )
        return AgentResult(
            data=data,
            sources=["supabase/news_events", "supabase/catalysts"],
            as_of=now,
            warnings=warnings,
        )

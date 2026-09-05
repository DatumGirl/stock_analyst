"""Graph agent: calls the graph service for relationship intelligence."""
from __future__ import annotations

import datetime
from typing import Any

import httpx

from .base import BaseAgent
from ..models import AgentResult


class GraphAgent(BaseAgent):
    def __init__(self, graph_service_url: str, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._graph_url = graph_service_url

    async def _graph_get(self, path: str) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(f"{self._graph_url}{path}", timeout=10.0)
            return res.json() if res.status_code == 200 else {}
        except httpx.RequestError:
            return {}

    async def _graph_post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(f"{self._graph_url}{path}", json=body, timeout=10.0)
            return res.json() if res.status_code == 200 else {}
        except httpx.RequestError:
            return {}

    async def run(self, ticker: str, portfolio_tickers: list[str] | None = None) -> AgentResult:  # type: ignore[override]
        today = datetime.date.today().isoformat()
        warnings: list[str] = []

        relationships = await self._graph_get(f"/relationships/{ticker}")
        supply_chain = await self._graph_get(f"/supply-chain/{ticker}")

        hidden: dict[str, Any] = {}
        if portfolio_tickers and len(portfolio_tickers) >= 2:
            hidden = await self._graph_post("/hidden-concentration", {"tickers": portfolio_tickers})

        if not relationships and not supply_chain:
            warnings.append(f"No graph relationships found for {ticker}")

        return AgentResult(
            data={
                "ticker": ticker,
                "relationships": relationships.get("data", []),
                "supply_chain": supply_chain.get("data", []),
                "hidden_concentration": hidden.get("data", []),
            },
            sources=[f"graph_service:{ticker}"],
            as_of=relationships.get("as_of", today) or today,
            warnings=warnings,
        )

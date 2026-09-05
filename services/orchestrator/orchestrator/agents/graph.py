"""Graph Intelligence Agent — calls the graph service for relationship data."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
from pydantic import BaseModel


class GraphRelationship(BaseModel):
    source_ticker: str
    target_ticker: str | None
    target_name: str
    rel_type: str
    weight: float
    direction: str
    as_of: str


class GraphData(BaseModel):
    ticker: str
    relationships: list[GraphRelationship]
    supply_chain_depth: int
    hidden_concentration: list[dict[str, Any]]
    as_of: str
    warnings: list[str]


class AgentResult(BaseModel):
    data: GraphData
    sources: list[str]
    as_of: str
    warnings: list[str]


class GraphAgent:
    def __init__(self, graph_url: str) -> None:
        self._url = graph_url

    async def run(
        self,
        ticker: str,
        portfolio_tickers: list[str],
        client: httpx.AsyncClient,
    ) -> AgentResult:
        warnings: list[str] = []
        now = datetime.now(timezone.utc).isoformat()
        relationships: list[GraphRelationship] = []
        hidden: list[dict[str, Any]] = []
        supply_chain_depth = 0

        # Direct relationships
        try:
            resp = await client.get(f"{self._url}/relationships/{ticker}", timeout=10.0)
            if resp.status_code == 200:
                payload = resp.json()
                raw_rels: list[dict[str, Any]] = payload.get("data", [])
                for r in raw_rels:
                    relationships.append(GraphRelationship(
                        source_ticker=ticker,
                        target_ticker=r.get("target"),
                        target_name=r.get("name", ""),
                        rel_type=r.get("type", "UNKNOWN"),
                        weight=float(r.get("weight", 0)),
                        direction=r.get("direction", "lateral"),
                        as_of=r.get("as_of", now),
                    ))
            else:
                warnings.append(f"Graph relationships unavailable: HTTP {resp.status_code}")
        except httpx.RequestError as e:
            warnings.append(f"Graph service unreachable: {e}")

        # Supply chain depth
        supply_tickers = [r for r in relationships if r.rel_type == "SUPPLIES"]
        supply_chain_depth = len(supply_tickers)

        # Hidden concentration across portfolio
        if len(portfolio_tickers) >= 2:
            try:
                hc_resp = await client.post(
                    f"{self._url}/hidden-concentration",
                    json={"tickers": portfolio_tickers},
                    timeout=10.0,
                )
                if hc_resp.status_code == 200:
                    hidden = hc_resp.json().get("data", [])
                else:
                    warnings.append(f"Hidden concentration unavailable: HTTP {hc_resp.status_code}")
            except httpx.RequestError as e:
                warnings.append(f"Graph service unreachable for hidden concentration: {e}")

        data = GraphData(
            ticker=ticker,
            relationships=relationships,
            supply_chain_depth=supply_chain_depth,
            hidden_concentration=hidden,
            as_of=now,
            warnings=warnings,
        )
        return AgentResult(data=data, sources=["graph_service"], as_of=now, warnings=warnings)

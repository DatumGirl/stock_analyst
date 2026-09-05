"""Load and execute Cypher query files against Memgraph."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from graph_service.schema import MemgraphQueryRunner, QueryRunner, RelationshipType, bind_query

QUERIES_DIR = Path(__file__).parent / "queries"


def load_query(name: str) -> str:
    path = QUERIES_DIR / f"{name}.cypher"
    if not path.exists():
        raise FileNotFoundError(f"Query file not found: {path}")
    return path.read_text()


class GraphQueries:
    def __init__(self, runner: QueryRunner) -> None:
        self._runner = runner
        self._queries = {
            "relationships": load_query("relationships"),
            "supply_chain": load_query("supply_chain"),
            "hidden_concentration": load_query("hidden_concentration"),
            "etf_overlap": load_query("etf_overlap"),
            "theme_exposure": load_query("theme_exposure"),
        }

    async def get_relationships(self, symbol: str) -> list[dict[str, Any]]:
        rows = await self._runner.execute(
            self._queries["relationships"], {"symbol": symbol.upper()}
        )
        if not rows:
            return []
        return rows[0].get("relationships", [])

    async def get_supply_chain(
        self, symbol: str, max_hops: int = 3
    ) -> list[dict[str, Any]]:
        query = bind_query(self._queries["supply_chain"], max_hops=max_hops)
        return await self._runner.execute(query, {"symbol": symbol.upper()})

    async def get_hidden_concentration(
        self, symbols: list[str]
    ) -> list[dict[str, Any]]:
        return await self._runner.execute(
            self._queries["hidden_concentration"],
            {"symbols": [s.upper() for s in symbols]},
        )

    async def get_etf_overlap(self, symbols: list[str]) -> list[dict[str, Any]]:
        return await self._runner.execute(
            self._queries["etf_overlap"],
            {"symbols": [s.upper() for s in symbols]},
        )

    async def get_theme_exposure(self, symbols: list[str]) -> list[dict[str, Any]]:
        return await self._runner.execute(
            self._queries["theme_exposure"],
            {"symbols": [s.upper() for s in symbols]},
        )

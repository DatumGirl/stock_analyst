"""Graph schema definitions and Memgraph query runner."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from neo4j import AsyncGraphDatabase, AsyncDriver

RelationshipType = Literal[
    "SUPPLIES",
    "COMPETES_WITH",
    "IS_CUSTOMER_OF",
    "PART_OF_ETF",
    "EXPOSED_TO_COUNTRY",
    "PART_OF_SECTOR",
    "EXPOSED_TO_THEME",
    "DEPENDS_ON_COMMODITY",
]

_ALLOWED_REL_TYPES: frozenset[str] = frozenset(RelationshipType.__args__)  # type: ignore[attr-defined]

MAX_HOPS = 5


class QueryRunner(Protocol):
    async def execute(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]: ...
    async def execute_write(self, query: str, params: dict[str, Any]) -> None: ...


class MemgraphQueryRunner:
    """Wraps the neo4j driver configured for Memgraph's Bolt endpoint."""

    def __init__(self, host: str = "localhost", port: int = 7687) -> None:
        uri = f"bolt://{host}:{port}"
        self._driver: AsyncDriver = AsyncGraphDatabase.driver(uri, auth=None)

    async def close(self) -> None:
        await self._driver.close()

    async def execute(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        async with self._driver.session() as session:
            result = await session.run(query, params)
            return [dict(record) async for record in result]

    async def execute_write(self, query: str, params: dict[str, Any]) -> None:
        async with self._driver.session() as session:
            await session.run(query, params)


def bind_query(
    query: str,
    rel_type: RelationshipType | None = None,
    max_hops: int | None = None,
) -> str:
    """Textually substitute rel_type and hop bounds after validation.

    Never interpolates arbitrary user input — only values from the schema enum.
    ADR 0001: Memgraph reserves 'hops'; use 'hop_count' in queries.
    """
    if rel_type is not None:
        if rel_type not in _ALLOWED_REL_TYPES:
            raise ValueError(f"Unknown relationship type: {rel_type!r}")
        query = query.replace("{{REL_TYPE}}", rel_type)

    if max_hops is not None:
        if not (1 <= max_hops <= MAX_HOPS):
            raise ValueError(f"max_hops must be 1–{MAX_HOPS}, got {max_hops}")
        query = query.replace("{{MAX_HOPS}}", str(max_hops))

    return query

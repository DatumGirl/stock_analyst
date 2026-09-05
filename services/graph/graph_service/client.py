"""The Memgraph I/O boundary.

Everything that touches the database lives here so the query builders, schema
validation and analysis logic stay pure and testable without a running instance.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from .config import MemgraphSettings
from .queries import BoundQuery, load_query, split_statements


class GraphConnectionError(RuntimeError):
    """Raised when Memgraph is unreachable or rejects a statement."""


@runtime_checkable
class QueryRunner(Protocol):
    """Minimal execution surface the service needs from a graph driver.

    Implemented by :class:`MemgraphClient` in production and by fakes in tests,
    so no test requires a live database.
    """

    def run(self, cypher: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a statement and return its rows as dictionaries."""
        ...


class MemgraphClient:
    """A thin, synchronous GQLAlchemy-backed :class:`QueryRunner`.

    The GQLAlchemy import is deferred to construction so importing the package —
    for schema validation or query building — never requires the driver.
    """

    def __init__(self, settings: MemgraphSettings) -> None:
        """Open a connection to Memgraph.

        Args:
            settings: Host, port, credentials and timeout to connect with.

        Raises:
            GraphConnectionError: If GQLAlchemy is not installed or the
                connection cannot be established.
        """
        try:
            from gqlalchemy import Memgraph
        except ImportError as exc:
            raise GraphConnectionError(
                "gqlalchemy is required to reach Memgraph; install services/graph dependencies"
            ) from exc

        self._settings = settings
        try:
            self._db = Memgraph(
                host=settings.host,
                port=settings.port,
                username=settings.username,
                password=settings.password,
                encrypted=settings.encrypted,
            )
        except Exception as exc:  # driver raises provider-specific errors
            raise GraphConnectionError(
                f"cannot connect to Memgraph at {settings.host}:{settings.port}: {exc}"
            ) from exc

    def run(self, cypher: str, parameters: dict[str, Any]) -> list[dict[str, Any]]:
        """Execute a statement against Memgraph.

        Args:
            cypher: The statement to run.
            parameters: Values bound by the driver.

        Returns:
            Result rows as dictionaries, empty when the statement returns nothing.

        Raises:
            GraphConnectionError: If the statement fails or the connection drops.
        """
        try:
            return [dict(row) for row in self._db.execute_and_fetch(cypher, parameters)]
        except Exception as exc:
            raise GraphConnectionError(
                f"Memgraph query failed at {self._settings.host}:{self._settings.port}: {exc}"
            ) from exc

    def execute(self, cypher: str, parameters: dict[str, Any]) -> None:
        """Execute a statement that returns no rows, such as a constraint.

        Args:
            cypher: The statement to run.
            parameters: Values bound by the driver.

        Raises:
            GraphConnectionError: If the statement fails.
        """
        try:
            self._db.execute(cypher, parameters)
        except Exception as exc:
            raise GraphConnectionError(
                f"Memgraph statement failed at {self._settings.host}:{self._settings.port}: {exc}"
            ) from exc


def run_bound(runner: QueryRunner, query: BoundQuery) -> list[dict[str, Any]]:
    """Execute a :class:`BoundQuery` on any runner.

    Args:
        runner: The execution surface to use.
        query: The bound statement and its parameters.

    Returns:
        Result rows as dictionaries.
    """
    return runner.run(query.cypher, query.parameters)


def apply_schema(client: MemgraphClient) -> list[str]:
    """Apply uniqueness constraints and indexes; safe to re-run.

    Memgraph raises when a constraint or index already exists, which is the
    normal outcome on every run after the first, so that specific outcome is
    recorded rather than raised.

    Args:
        client: A connected Memgraph client.

    Returns:
        Statements that were newly applied, in file order.

    Raises:
        GraphConnectionError: If a statement fails for a reason other than the
            constraint or index already existing.
    """
    applied: list[str] = []
    for statement in split_statements(load_query("schema_constraints")):
        try:
            client.execute(statement, {})
        except GraphConnectionError as exc:
            if "already exist" not in str(exc).lower():
                raise
            continue
        applied.append(statement)
    return applied

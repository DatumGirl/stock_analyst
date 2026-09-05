"""The typed result envelope every graph agent function returns.

Per CLAUDE.md section 7, an agent result carries ``data``, ``sources``,
``as_of`` and ``warnings``. Missing values are reported as ``None`` plus a
warning; they are never estimated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


#: Row keys that carry source identifiers, as a scalar or a (possibly nested) list.
SOURCE_KEYS = ("source", "sources")
#: Row keys that carry as_of dates. ``oldest_as_of`` is what determines the
#: freshness a caller must display, so aggregate rows expose it under this name.
AS_OF_KEYS = ("as_of", "as_of_dates", "oldest_as_of")


@dataclass(slots=True)
class GraphResult:
    """A JSON-serialisable answer from the Graph agent.

    Args:
        query: Name of the graph question answered, e.g. ``"hidden_concentration"``.
        data: Rows the query produced; empty when nothing matched.
        sources: Distinct provenance identifiers behind the rows.
        as_of: Oldest ``as_of`` across the rows — the freshness the caller must
            display. ``None`` when no row carried a date.
        warnings: Human-readable notes about staleness, missing nodes or
            truncation. Never silently dropped.
    """

    query: str
    data: list[dict[str, Any]] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    as_of: date | None = None
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return the result as plain JSON-compatible types."""
        return {
            "query": self.query,
            "data": self.data,
            "sources": self.sources,
            "as_of": self.as_of.isoformat() if self.as_of else None,
            "warnings": self.warnings,
        }


def summarize_provenance(rows: list[dict[str, Any]]) -> tuple[list[str], date | None]:
    """Collect distinct sources and the oldest ``as_of`` across result rows.

    Rows may carry provenance as a scalar (``source``/``as_of``) or as a list
    (``sources``/``as_of_dates``) when the value was aggregated along a path.

    Args:
        rows: Result rows returned by a Cypher query.

    Returns:
        A ``(sources, oldest_as_of)`` pair; ``oldest_as_of`` is ``None`` when no
        row carried a parseable date.
    """
    sources: set[str] = set()
    dates: list[date] = []
    for row in rows:
        for key in SOURCE_KEYS:
            sources.update(_collect_strings(row.get(key)))
        for key in AS_OF_KEYS:
            dates.extend(_collect_dates(row.get(key)))
    return sorted(sources), min(dates) if dates else None


def _collect_strings(value: Any) -> list[str]:
    """Flatten a scalar or nested list of source identifiers into a string list."""
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, (list, tuple)):
        return [item for element in value for item in _collect_strings(element)]
    return []


def _collect_dates(value: Any) -> list[date]:
    """Flatten a scalar or nested list of dates, ignoring unparseable entries."""
    if value is None:
        return []
    if isinstance(value, date):
        return [value]
    if isinstance(value, str):
        try:
            return [date.fromisoformat(value)]
        except ValueError:
            return []
    if isinstance(value, (list, tuple)):
        return [item for element in value for item in _collect_dates(element)]
    return []

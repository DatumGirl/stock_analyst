"""Loading and safe binding of the Cypher files in ``services/graph/queries``.

Cypher parameters cannot stand in for labels, relationship types, or the bounds
of a variable-length pattern, so those placeholders are substituted textually.
To keep that safe, every substituted value must come from the schema enums or be
a non-negative integer — arbitrary strings are rejected before they reach the
database. Values remain real query parameters.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from .schema import NodeLabel, RelType

QUERY_DIR = Path(__file__).resolve().parent.parent / "queries"
QUERY_SUFFIX = ".cypher"

#: Placeholders that name graph structure and therefore cannot be parameters.
LABEL_PLACEHOLDERS = frozenset({"label", "start_label", "end_label"})
REL_TYPE_PLACEHOLDERS = frozenset({"rel_type"})
BOUND_PLACEHOLDERS = frozenset({"max_hops"})

_PLACEHOLDER_PATTERN = re.compile(r"\$([a-z_]+)")
MAX_TRAVERSAL_HOPS = 10


class QueryError(RuntimeError):
    """Raised when a Cypher file is missing or bound with an unsafe value."""


@dataclass(frozen=True, slots=True)
class BoundQuery:
    """A Cypher statement with structural placeholders resolved.

    Args:
        name: The query file's stem, e.g. ``"supply_chain"``.
        cypher: The statement ready to execute.
        parameters: Values bound as real query parameters.
    """

    name: str
    cypher: str
    parameters: dict[str, Any]


@lru_cache(maxsize=None)
def load_query(name: str) -> str:
    """Read a Cypher file from the query directory.

    Args:
        name: File stem without the ``.cypher`` suffix.

    Returns:
        The raw statement text.

    Raises:
        QueryError: If the name escapes the query directory or has no file.
    """
    if not name.isidentifier():
        raise QueryError(f"query name {name!r} is not a bare identifier")
    path = QUERY_DIR / f"{name}{QUERY_SUFFIX}"
    if not path.is_file():
        available = sorted(p.stem for p in QUERY_DIR.glob(f"*{QUERY_SUFFIX}"))
        raise QueryError(f"no query named {name!r} in {QUERY_DIR}; have {available}")
    return path.read_text(encoding="utf-8")


def bind_query(name: str, **values: Any) -> BoundQuery:
    """Resolve a query's structural placeholders and split off its parameters.

    Structural placeholders (labels, relationship types, traversal bounds) are
    substituted into the text after validation; everything else is returned as a
    parameter dictionary for the driver to bind.

    Args:
        name: File stem of the query to load.
        **values: Values for every ``$placeholder`` the statement uses.

    Returns:
        The bound query.

    Raises:
        QueryError: If a placeholder has no value, a structural value is not a
            known label/relationship type/valid bound, or a value is unused.
    """
    cypher = load_query(name)
    placeholders = set(_PLACEHOLDER_PATTERN.findall(cypher))
    missing = placeholders - values.keys()
    if missing:
        raise QueryError(f"query {name!r} needs values for {sorted(missing)}")
    unused = values.keys() - placeholders
    if unused:
        raise QueryError(f"query {name!r} does not use {sorted(unused)}")

    parameters: dict[str, Any] = {}
    for placeholder, value in values.items():
        if placeholder in LABEL_PLACEHOLDERS:
            cypher = cypher.replace(f"${placeholder}", _safe_label(name, placeholder, value))
        elif placeholder in REL_TYPE_PLACEHOLDERS:
            cypher = cypher.replace(f"${placeholder}", _safe_rel_type(name, placeholder, value))
        elif placeholder in BOUND_PLACEHOLDERS:
            cypher = cypher.replace(f"${placeholder}", _safe_bound(name, placeholder, value))
        else:
            parameters[placeholder] = value
    return BoundQuery(name=name, cypher=cypher, parameters=parameters)


def split_statements(script: str) -> list[str]:
    """Split a multi-statement Cypher script into individually runnable statements.

    Comment-only lines are dropped so drivers that reject empty statements do not
    choke on the file headers.

    Args:
        script: Raw contents of a ``.cypher`` file.

    Returns:
        Statements without trailing semicolons, in file order.
    """
    lines = [line for line in script.splitlines() if not line.strip().startswith("//")]
    return [stmt.strip() for stmt in "\n".join(lines).split(";") if stmt.strip()]


def _safe_label(query_name: str, placeholder: str, value: Any) -> str:
    """Validate a node label for textual substitution.

    Raises:
        QueryError: If the value is not a member of :class:`NodeLabel`.
    """
    try:
        return NodeLabel(value).value
    except ValueError as exc:
        raise QueryError(
            f"query {query_name!r} placeholder ${placeholder} must be a NodeLabel, got {value!r}"
        ) from exc


def _safe_rel_type(query_name: str, placeholder: str, value: Any) -> str:
    """Validate a relationship type for textual substitution.

    Raises:
        QueryError: If the value is not a member of :class:`RelType`.
    """
    try:
        return RelType(value).value
    except ValueError as exc:
        raise QueryError(
            f"query {query_name!r} placeholder ${placeholder} must be a RelType, got {value!r}"
        ) from exc


def _safe_bound(query_name: str, placeholder: str, value: Any) -> str:
    """Validate a variable-length traversal bound for textual substitution.

    Raises:
        QueryError: If the value is not an integer in [1, MAX_TRAVERSAL_HOPS].
    """
    if not isinstance(value, int) or isinstance(value, bool):
        raise QueryError(
            f"query {query_name!r} placeholder ${placeholder} must be an int, got {value!r}"
        )
    if not 1 <= value <= MAX_TRAVERSAL_HOPS:
        raise QueryError(
            f"query {query_name!r} placeholder ${placeholder} must be in "
            f"[1, {MAX_TRAVERSAL_HOPS}], got {value}"
        )
    return str(value)

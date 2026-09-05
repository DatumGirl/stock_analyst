"""Graph schema: node labels, relationship types and property contracts.

The graph stores *relationships only*. Time-series (prices, fundamentals) and
user-owned data (portfolios, positions) live in Postgres and are never
duplicated here, per CLAUDE.md section 2.

Every fact node carries provenance (``source``, ``as_of``); a node without it is
a bug, so :func:`Provenance.validate` fails loudly at the ingestion boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from typing import Any


class NodeLabel(str, Enum):
    """Node labels present in the graph."""

    COMPANY = "Company"
    SECTOR = "Sector"
    INDUSTRY = "Industry"
    ETF = "ETF"
    COUNTRY = "Country"
    COMMODITY = "Commodity"
    TECHNOLOGY = "Technology"
    THEME = "Theme"
    RISK_FACTOR = "RiskFactor"
    NEWS_EVENT = "NewsEvent"
    MACRO_EVENT = "MacroEvent"


class RelType(str, Enum):
    """Relationship types present in the graph."""

    SUPPLIES = "SUPPLIES"          # (Company)-[:SUPPLIES]->(Company)
    CUSTOMER_OF = "CUSTOMER_OF"    # (Company)-[:CUSTOMER_OF]->(Company)
    COMPETES_WITH = "COMPETES_WITH"
    IN_SECTOR = "IN_SECTOR"
    IN_INDUSTRY = "IN_INDUSTRY"
    HELD_BY = "HELD_BY"            # (Company)-[:HELD_BY]->(ETF)
    OPERATES_IN = "OPERATES_IN"    # (Company)-[:OPERATES_IN]->(Country)
    DEPENDS_ON = "DEPENDS_ON"      # (Company)-[:DEPENDS_ON]->(Commodity|Technology)
    EXPOSED_TO = "EXPOSED_TO"      # (Company)-[:EXPOSED_TO]->(RiskFactor)
    PART_OF_THEME = "PART_OF_THEME"
    AFFECTS = "AFFECTS"            # (NewsEvent|MacroEvent)-[:AFFECTS]->(*)


#: Relationship types whose weight expresses an exposure fraction in [0, 1].
FRACTIONAL_REL_TYPES: frozenset[RelType] = frozenset(
    {
        RelType.SUPPLIES,
        RelType.CUSTOMER_OF,
        RelType.HELD_BY,
        RelType.OPERATES_IN,
        RelType.DEPENDS_ON,
    }
)

MIN_WEIGHT = 0.0
MAX_WEIGHT = 1.0
MIN_CONFIDENCE = 0.0
MAX_CONFIDENCE = 1.0


class ProvenanceError(ValueError):
    """Raised when a node or edge reaches the graph without valid provenance."""


@dataclass(frozen=True, slots=True)
class Provenance:
    """Where a fact came from and when it was true.

    Args:
        source: Provider or document identifier, e.g. ``"sec:10-K:0000320193-24"``.
        as_of: The date the fact was asserted by that source.
        confidence: How strongly the source supports the fact, in [0, 1].
    """

    source: str
    as_of: date
    confidence: float = MAX_CONFIDENCE

    def validate(self) -> None:
        """Reject provenance that would make a graph fact unauditable.

        Raises:
            ProvenanceError: If the source is blank, ``as_of`` is in the future,
                or confidence falls outside [0, 1].
        """
        if not self.source.strip():
            raise ProvenanceError("provenance requires a non-empty source")
        if self.as_of > datetime.now(timezone.utc).date():
            raise ProvenanceError(
                f"provenance as_of {self.as_of.isoformat()} is in the future"
            )
        if not MIN_CONFIDENCE <= self.confidence <= MAX_CONFIDENCE:
            raise ProvenanceError(
                f"confidence {self.confidence} outside "
                f"[{MIN_CONFIDENCE}, {MAX_CONFIDENCE}] for source {self.source!r}"
            )

    def as_properties(self) -> dict[str, Any]:
        """Return provenance as Cypher-ready property values."""
        return {
            "source": self.source,
            "as_of": self.as_of.isoformat(),
            "confidence": self.confidence,
        }


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A node destined for the graph, keyed uniquely by ``(label, key)``.

    Args:
        label: The node's label.
        key: Natural key, unique within the label (ticker, theme slug, ...).
        properties: Additional non-key properties, e.g. ``name``.
        provenance: Where the node's assertion came from.
    """

    label: NodeLabel
    key: str
    provenance: Provenance
    properties: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Reject nodes that cannot be identified or audited.

        Raises:
            ProvenanceError: If provenance is invalid.
            ValueError: If the natural key is blank.
        """
        if not self.key.strip():
            raise ValueError(f"{self.label.value} node requires a non-empty key")
        self.provenance.validate()


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """A directed relationship between two nodes.

    Args:
        rel_type: The relationship type.
        start: Source node reference as ``(label, key)``.
        end: Target node reference as ``(label, key)``.
        weight: Strength of the relationship; an exposure fraction in [0, 1] for
            :data:`FRACTIONAL_REL_TYPES`, otherwise an unconstrained score.
        provenance: Where the relationship assertion came from.
        properties: Additional non-key properties.
    """

    rel_type: RelType
    start: tuple[NodeLabel, str]
    end: tuple[NodeLabel, str]
    provenance: Provenance
    weight: float | None = None
    properties: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        """Reject edges that are self-referential, unweighted where required, or unauditable.

        Raises:
            ProvenanceError: If provenance is invalid.
            ValueError: If the edge is a self-loop or its weight is out of range.
        """
        if self.start == self.end:
            raise ValueError(
                f"{self.rel_type.value} self-loop on {self.start[1]!r} is not a relationship"
            )
        if self.rel_type in FRACTIONAL_REL_TYPES:
            if self.weight is None:
                raise ValueError(
                    f"{self.rel_type.value} from {self.start[1]!r} to {self.end[1]!r} "
                    "requires a weight expressing exposure fraction"
                )
            if not MIN_WEIGHT <= self.weight <= MAX_WEIGHT:
                raise ValueError(
                    f"{self.rel_type.value} weight {self.weight} outside "
                    f"[{MIN_WEIGHT}, {MAX_WEIGHT}] for {self.start[1]!r}->{self.end[1]!r}"
                )
        self.provenance.validate()

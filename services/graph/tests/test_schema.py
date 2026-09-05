"""Schema validation: provenance, node keys and edge weight contracts."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from graph_service.schema import (
    GraphEdge,
    GraphNode,
    NodeLabel,
    Provenance,
    ProvenanceError,
    RelType,
)

TODAY = date(2026, 9, 5)
VALID_PROVENANCE = Provenance(source="sec:10-K:0000320193-24", as_of=TODAY)


def test_provenance_accepts_a_sourced_past_dated_fact() -> None:
    Provenance(source="fmp:profile", as_of=TODAY - timedelta(days=1)).validate()


def test_provenance_rejects_blank_source() -> None:
    with pytest.raises(ProvenanceError, match="non-empty source"):
        Provenance(source="   ", as_of=TODAY).validate()


def test_provenance_rejects_future_as_of() -> None:
    future = date.today() + timedelta(days=2)
    with pytest.raises(ProvenanceError, match="in the future"):
        Provenance(source="fmp:profile", as_of=future).validate()


def test_provenance_rejects_confidence_above_one() -> None:
    with pytest.raises(ProvenanceError, match="outside"):
        Provenance(source="fmp:profile", as_of=TODAY, confidence=1.5).validate()


def test_node_rejects_blank_key() -> None:
    node = GraphNode(label=NodeLabel.COMPANY, key="  ", provenance=VALID_PROVENANCE)
    with pytest.raises(ValueError, match="non-empty key"):
        node.validate()


def test_node_accepts_valid_company() -> None:
    node = GraphNode(
        label=NodeLabel.COMPANY,
        key="NVDA",
        provenance=VALID_PROVENANCE,
        properties={"name": "NVIDIA Corporation"},
    )
    node.validate()


def test_edge_rejects_self_loop() -> None:
    edge = GraphEdge(
        rel_type=RelType.COMPETES_WITH,
        start=(NodeLabel.COMPANY, "NVDA"),
        end=(NodeLabel.COMPANY, "NVDA"),
        provenance=VALID_PROVENANCE,
    )
    with pytest.raises(ValueError, match="self-loop"):
        edge.validate()


def test_edge_requires_weight_for_fractional_relationship() -> None:
    edge = GraphEdge(
        rel_type=RelType.SUPPLIES,
        start=(NodeLabel.COMPANY, "TSM"),
        end=(NodeLabel.COMPANY, "NVDA"),
        provenance=VALID_PROVENANCE,
    )
    with pytest.raises(ValueError, match="requires a weight"):
        edge.validate()


def test_edge_rejects_weight_above_one() -> None:
    edge = GraphEdge(
        rel_type=RelType.SUPPLIES,
        start=(NodeLabel.COMPANY, "TSM"),
        end=(NodeLabel.COMPANY, "NVDA"),
        provenance=VALID_PROVENANCE,
        weight=1.4,
    )
    with pytest.raises(ValueError, match="outside"):
        edge.validate()


def test_edge_allows_unweighted_non_fractional_relationship() -> None:
    edge = GraphEdge(
        rel_type=RelType.COMPETES_WITH,
        start=(NodeLabel.COMPANY, "NVDA"),
        end=(NodeLabel.COMPANY, "AMD"),
        provenance=VALID_PROVENANCE,
    )
    edge.validate()


def test_edge_allows_boundary_weights() -> None:
    for weight in (0.0, 1.0):
        GraphEdge(
            rel_type=RelType.HELD_BY,
            start=(NodeLabel.COMPANY, "NVDA"),
            end=(NodeLabel.ETF, "SMH"),
            provenance=VALID_PROVENANCE,
            weight=weight,
        ).validate()

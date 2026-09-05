"""Ingestion ordering, idempotent upserts and skipped-edge reporting."""

from __future__ import annotations

from datetime import date

import pytest

from graph_service.ingest import ingest
from graph_service.schema import GraphEdge, GraphNode, NodeLabel, Provenance, RelType

PROVENANCE = Provenance(source="sec:10-K:0000320193-24", as_of=date(2026, 6, 30))

NVDA = GraphNode(label=NodeLabel.COMPANY, key="NVDA", provenance=PROVENANCE, properties={"name": "NVIDIA"})
TSM = GraphNode(label=NodeLabel.COMPANY, key="TSM", provenance=PROVENANCE, properties={"name": "TSMC"})
SUPPLIES_EDGE = GraphEdge(
    rel_type=RelType.SUPPLIES,
    start=(NodeLabel.COMPANY, "TSM"),
    end=(NodeLabel.COMPANY, "NVDA"),
    provenance=PROVENANCE,
    weight=0.6,
)


def test_ingest_writes_nodes_before_edges(runner) -> None:
    runner.rows = [{"start_key": "TSM", "end_key": "NVDA"}]
    report = ingest(runner, [NVDA, TSM], [SUPPLIES_EDGE])

    assert report.nodes_written == 2
    assert report.edges_written == 1
    assert report.skipped_edges == []
    node_calls = [c for c in runner.calls if "MERGE (n:Company" in c[0]]
    edge_calls = [c for c in runner.calls if "[r:SUPPLIES]" in c[0]]
    assert runner.calls.index(node_calls[-1]) < runner.calls.index(edge_calls[0])


def test_ingest_reports_edge_with_missing_endpoint(runner) -> None:
    runner.rows = []
    report = ingest(runner, [], [SUPPLIES_EDGE])

    assert report.edges_written == 0
    assert len(report.skipped_edges) == 1
    assert "endpoints do not exist" in report.skipped_edges[0]


def test_ingest_validates_before_writing_anything(runner) -> None:
    unweighted = GraphEdge(
        rel_type=RelType.SUPPLIES,
        start=(NodeLabel.COMPANY, "TSM"),
        end=(NodeLabel.COMPANY, "NVDA"),
        provenance=PROVENANCE,
    )
    with pytest.raises(ValueError, match="requires a weight"):
        ingest(runner, [NVDA, TSM], [unweighted])
    assert runner.calls == []


def test_ingest_passes_provenance_as_parameters(runner) -> None:
    runner.rows = [{"key": "NVDA"}]
    ingest(runner, [NVDA], [])

    _, parameters = runner.calls[0]
    assert parameters["source"] == "sec:10-K:0000320193-24"
    assert parameters["as_of"] == "2026-06-30"
    assert parameters["confidence"] == 1.0


def test_ingest_of_empty_batch_writes_nothing(runner) -> None:
    report = ingest(runner, [], [])
    assert (report.nodes_written, report.edges_written) == (0, 0)
    assert runner.calls == []

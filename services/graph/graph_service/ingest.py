"""Ingestion of relationship facts into the graph.

Ingestion is validate-then-write: every node and edge is checked against the
schema contract before any statement runs, so a bad batch fails before it can
half-apply. Writes are idempotent, making backfills safe to re-run.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .client import QueryRunner, run_bound
from .queries import bind_query
from .schema import GraphEdge, GraphNode


@dataclass(slots=True)
class IngestReport:
    """What an ingestion run wrote and what it could not write.

    Args:
        nodes_written: Count of node upserts that succeeded.
        edges_written: Count of edge upserts that succeeded.
        skipped_edges: Edges whose endpoints were absent, with the reason.
    """

    nodes_written: int = 0
    edges_written: int = 0
    skipped_edges: list[str] = field(default_factory=list)


def ingest(
    runner: QueryRunner,
    nodes: list[GraphNode],
    edges: list[GraphEdge],
) -> IngestReport:
    """Validate and upsert a batch of nodes and edges.

    Nodes are written before edges so that relationships in the same batch find
    their endpoints. An edge whose endpoints are still missing is skipped and
    reported rather than conjuring an unprovenanced node.

    Args:
        runner: Execution surface to write through.
        nodes: Nodes to upsert.
        edges: Edges to upsert.

    Returns:
        A report of what was written and what was skipped.

    Raises:
        ValueError: If any node or edge fails schema validation.
        ProvenanceError: If any node or edge lacks valid provenance.
    """
    for node in nodes:
        node.validate()
    for edge in edges:
        edge.validate()

    report = IngestReport()
    for node in nodes:
        query = bind_query(
            "upsert_node",
            label=node.label,
            key=node.key,
            properties=node.properties,
            **node.provenance.as_properties(),
        )
        run_bound(runner, query)
        report.nodes_written += 1

    for edge in edges:
        query = bind_query(
            "upsert_edge",
            rel_type=edge.rel_type,
            start_label=edge.start[0],
            start_key=edge.start[1],
            end_label=edge.end[0],
            end_key=edge.end[1],
            weight=edge.weight,
            properties=edge.properties,
            **edge.provenance.as_properties(),
        )
        if run_bound(runner, query):
            report.edges_written += 1
        else:
            report.skipped_edges.append(
                f"{edge.rel_type.value} {edge.start[1]!r}->{edge.end[1]!r}: "
                "one or both endpoints do not exist in the graph"
            )
    return report

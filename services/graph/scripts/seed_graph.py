"""Seed the local graph with a small, realistic semiconductor relationship set.

This is development fixture data, not a production ingestion path. Every fact
carries a source and an as_of so the seeded graph exercises the same provenance
contract as real data. Production relationships are ingested from filings and
provider feeds through :func:`graph_service.ingest.ingest`.

Usage:
    MEMGRAPH_USERNAME=... MEMGRAPH_PASSWORD=... python scripts/seed_graph.py
"""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from graph_service.client import MemgraphClient, apply_schema
from graph_service.config import load_config
from graph_service.ingest import ingest
from graph_service.schema import GraphEdge, GraphNode, NodeLabel, Provenance, RelType

FILING_SOURCE = "sec:10-K:fixture"
ETF_SOURCE = "provider:etf-holdings:fixture"
ANALYST_SOURCE = "analyst:manual:fixture"
AS_OF = date(2026, 6, 30)

FILING = Provenance(source=FILING_SOURCE, as_of=AS_OF)
ETF_HOLDINGS = Provenance(source=ETF_SOURCE, as_of=AS_OF, confidence=0.95)
ANALYST = Provenance(source=ANALYST_SOURCE, as_of=AS_OF, confidence=0.7)

COMPANIES = {
    "NVDA": "NVIDIA Corporation",
    "AMD": "Advanced Micro Devices",
    "AVGO": "Broadcom Inc.",
    "MU": "Micron Technology",
    "TSM": "Taiwan Semiconductor Manufacturing",
    "ASML": "ASML Holding",
    "MSFT": "Microsoft Corporation",
}


def build_nodes() -> list[GraphNode]:
    """Return the fixture's nodes across every label the queries traverse."""
    companies = [
        GraphNode(NodeLabel.COMPANY, ticker, FILING, {"name": name})
        for ticker, name in COMPANIES.items()
    ]
    context = [
        GraphNode(NodeLabel.SECTOR, "information-technology", FILING, {"name": "Information Technology"}),
        GraphNode(NodeLabel.INDUSTRY, "semiconductors", FILING, {"name": "Semiconductors"}),
        GraphNode(NodeLabel.ETF, "SMH", ETF_HOLDINGS, {"name": "VanEck Semiconductor ETF"}),
        GraphNode(NodeLabel.ETF, "QQQ", ETF_HOLDINGS, {"name": "Invesco QQQ Trust"}),
        GraphNode(NodeLabel.COUNTRY, "TW", FILING, {"name": "Taiwan"}),
        GraphNode(NodeLabel.COUNTRY, "US", FILING, {"name": "United States"}),
        GraphNode(NodeLabel.COMMODITY, "advanced-node-wafers", ANALYST, {"name": "Advanced-node wafers"}),
        GraphNode(NodeLabel.TECHNOLOGY, "euv-lithography", ANALYST, {"name": "EUV lithography"}),
        GraphNode(NodeLabel.THEME, "ai-infrastructure", ANALYST, {"name": "AI Infrastructure"}),
        GraphNode(NodeLabel.RISK_FACTOR, "taiwan-strait-geopolitics", ANALYST, {"name": "Taiwan Strait geopolitical risk"}),
        GraphNode(NodeLabel.NEWS_EVENT, "news:taiwan-fab-disruption", ANALYST, {"headline": "Fab output disrupted in Taiwan"}),
    ]
    return companies + context


def build_edges() -> list[GraphEdge]:
    """Return the fixture's relationships, including the shared TSMC dependency.

    Four holdings depend on TSMC and on Taiwan, which is the hidden concentration
    that sector allocation alone would not reveal.
    """
    company = NodeLabel.COMPANY
    fab_dependents = ["NVDA", "AMD", "AVGO", "MU"]

    supply = [
        GraphEdge(RelType.SUPPLIES, (company, "TSM"), (company, ticker), FILING, weight=weight)
        for ticker, weight in [("NVDA", 0.85), ("AMD", 0.80), ("AVGO", 0.55), ("MU", 0.25)]
    ]
    supply.append(
        GraphEdge(RelType.SUPPLIES, (company, "ASML"), (company, "TSM"), FILING, weight=0.70)
    )
    customers = [
        GraphEdge(RelType.CUSTOMER_OF, (company, "NVDA"), (company, "MSFT"), FILING, weight=0.19),
    ]
    competitors = [
        GraphEdge(RelType.COMPETES_WITH, (company, "NVDA"), (company, "AMD"), ANALYST),
        GraphEdge(RelType.COMPETES_WITH, (company, "AVGO"), (company, "NVDA"), ANALYST),
    ]
    classification = [
        GraphEdge(RelType.IN_INDUSTRY, (company, t), (NodeLabel.INDUSTRY, "semiconductors"), FILING)
        for t in fab_dependents + ["TSM", "ASML"]
    ] + [
        GraphEdge(RelType.IN_SECTOR, (company, t), (NodeLabel.SECTOR, "information-technology"), FILING)
        for t in COMPANIES
    ]
    etfs = [
        GraphEdge(RelType.HELD_BY, (company, t), (NodeLabel.ETF, "SMH"), ETF_HOLDINGS, weight=w)
        for t, w in [("NVDA", 0.19), ("AMD", 0.06), ("AVGO", 0.09), ("MU", 0.05), ("TSM", 0.11)]
    ] + [
        GraphEdge(RelType.HELD_BY, (company, t), (NodeLabel.ETF, "QQQ"), ETF_HOLDINGS, weight=w)
        for t, w in [("NVDA", 0.08), ("AVGO", 0.05), ("MSFT", 0.08)]
    ]
    geography = [
        GraphEdge(RelType.OPERATES_IN, (company, "TSM"), (NodeLabel.COUNTRY, "TW"), FILING, weight=0.90),
    ] + [
        GraphEdge(RelType.OPERATES_IN, (company, t), (NodeLabel.COUNTRY, "US"), FILING, weight=0.60)
        for t in ["NVDA", "AMD", "AVGO", "MU", "MSFT"]
    ]
    dependencies = [
        GraphEdge(RelType.DEPENDS_ON, (company, t), (NodeLabel.COMMODITY, "advanced-node-wafers"), ANALYST, weight=w)
        for t, w in [("NVDA", 0.80), ("AMD", 0.75), ("AVGO", 0.50)]
    ] + [
        GraphEdge(RelType.DEPENDS_ON, (company, "TSM"), (NodeLabel.TECHNOLOGY, "euv-lithography"), ANALYST, weight=0.65),
    ]
    themes = [
        GraphEdge(RelType.PART_OF_THEME, (company, t), (NodeLabel.THEME, "ai-infrastructure"), ANALYST, weight=w)
        for t, w in [("NVDA", 0.9), ("AMD", 0.6), ("AVGO", 0.5), ("MU", 0.4), ("MSFT", 0.5)]
    ]
    risks = [
        GraphEdge(RelType.EXPOSED_TO, (company, t), (NodeLabel.RISK_FACTOR, "taiwan-strait-geopolitics"), ANALYST, weight=0.7)
        for t in fab_dependents
    ]
    events = [
        GraphEdge(
            RelType.AFFECTS,
            (NodeLabel.NEWS_EVENT, "news:taiwan-fab-disruption"),
            (company, "TSM"),
            ANALYST,
            weight=0.8,
        ),
    ]
    return (
        supply + customers + competitors + classification + etfs
        + geography + dependencies + themes + risks + events
    )


def main() -> int:
    """Apply the schema and load the fixture graph.

    Returns:
        Process exit code: 0 on success, 1 when edges could not be written.
    """
    config = load_config()
    client = MemgraphClient(config.memgraph)
    applied = apply_schema(client)
    print(f"schema: {len(applied)} statement(s) newly applied")

    report = ingest(client, build_nodes(), build_edges())
    print(f"seeded {report.nodes_written} nodes and {report.edges_written} edges")
    for skipped in report.skipped_edges:
        print(f"  skipped: {skipped}", file=sys.stderr)
    return 1 if report.skipped_edges else 0


if __name__ == "__main__":
    raise SystemExit(main())

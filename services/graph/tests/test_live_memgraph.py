"""Integration tests against a live Memgraph instance.

These exercise the Cypher itself — parse errors, reserved words and traversal
direction are invisible to tests that stub the driver. Skipped unless
MEMGRAPH_USERNAME/PASSWORD are set and the instance is reachable; run
``docker compose up -d`` and ``python scripts/seed_graph.py`` first.
"""

from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from graph_service.agent import (  # noqa: E402
    company_relationships,
    data_freshness,
    etf_overlap,
    event_propagation,
    hidden_concentration,
    peer_group,
    supply_chain,
    theme_exposure,
)
from graph_service.client import GraphConnectionError, MemgraphClient, apply_schema  # noqa: E402
from graph_service.config import load_config  # noqa: E402
from graph_service.ingest import ingest  # noqa: E402

SEED_AS_OF = date(2026, 6, 30)
TODAY = date(2026, 9, 5)
PORTFOLIO = ["NVDA", "AMD", "AVGO", "MU"]
FAB_EVENT = "news:taiwan-fab-disruption"


@pytest.fixture(scope="module")
def live_graph():
    """Connect to Memgraph and load the fixture graph, or skip the module."""
    if not os.environ.get("MEMGRAPH_PASSWORD"):
        pytest.skip("MEMGRAPH_PASSWORD unset; skipping live Memgraph tests")
    try:
        config = load_config()
        client = MemgraphClient(config.memgraph)
        client.run("RETURN 1 AS ok", {})
    except GraphConnectionError as exc:
        pytest.skip(f"Memgraph unreachable: {exc}")

    from seed_graph import build_edges, build_nodes

    apply_schema(client)
    ingest(client, build_nodes(), build_edges())
    return client, config.traversal


def test_every_query_parses_and_returns_rows(live_graph) -> None:
    """A Cypher syntax error — a reserved word, say — fails here and nowhere else."""
    client, traversal = live_graph
    results = [
        company_relationships(client, "NVDA", traversal, TODAY),
        supply_chain(client, "NVDA", traversal, TODAY),
        etf_overlap(client, PORTFOLIO, traversal, TODAY),
        hidden_concentration(client, PORTFOLIO, traversal, TODAY),
        event_propagation(client, FAB_EVENT, traversal, PORTFOLIO, TODAY),
        peer_group(client, "NVDA", 10, TODAY),
        theme_exposure(client, PORTFOLIO, traversal, TODAY),
        data_freshness(client, TODAY),
    ]
    empty = [r.query for r in results if not r.data]
    assert not empty, f"queries returned no rows against the seeded graph: {empty}"


def test_supply_chain_traverses_upstream_beyond_one_hop(live_graph) -> None:
    client, traversal = live_graph
    result = supply_chain(client, "NVDA", traversal, TODAY)
    by_supplier = {row["supplier_key"]: row for row in result.data}

    assert by_supplier["TSM"]["hop_count"] == 1
    assert by_supplier["ASML"]["hop_count"] == 2, "supplier-of-supplier not reached"
    assert by_supplier["ASML"]["cumulative_weight"] < by_supplier["TSM"]["cumulative_weight"]


def test_event_at_a_supplier_propagates_downstream_to_its_customers(live_graph) -> None:
    """A fab disruption must reach the companies TSMC supplies, not its own suppliers."""
    client, traversal = live_graph
    result = event_propagation(client, FAB_EVENT, traversal, PORTFOLIO, TODAY)
    reached = {row["ticker"]: row for row in result.data}

    assert "NVDA" in reached, "event did not propagate downstream to TSMC's customers"
    assert reached["NVDA"]["via"] == ["TSM"]
    assert reached["NVDA"]["impact_score"] > reached["MU"]["impact_score"], (
        "impact must rank by supply dependency"
    )


def test_event_impact_decays_with_distance(live_graph) -> None:
    client, traversal = live_graph
    result = event_propagation(client, FAB_EVENT, traversal, None, TODAY)
    by_ticker = {row["ticker"]: row for row in result.data}

    assert by_ticker["TSM"]["hop_count"] == 0
    assert by_ticker["TSM"]["impact_score"] > by_ticker["NVDA"]["impact_score"]


def test_hidden_concentration_finds_the_shared_taiwan_dependency(live_graph) -> None:
    client, traversal = live_graph
    result = hidden_concentration(client, PORTFOLIO, traversal, TODAY)
    by_dependency = {row["dependency_key"]: row for row in result.data}

    taiwan_risk = by_dependency["taiwan-strait-geopolitics"]
    assert taiwan_risk["affected_count"] == len(PORTFOLIO)
    assert sorted(taiwan_risk["affected_tickers"]) == sorted(PORTFOLIO)


def test_hidden_concentration_excludes_the_holdings_themselves(live_graph) -> None:
    client, traversal = live_graph
    result = hidden_concentration(client, PORTFOLIO, traversal, TODAY)

    assert all(row["dependency_key"] not in PORTFOLIO for row in result.data)


def test_etf_overlap_reports_only_multi_holding_funds(live_graph) -> None:
    client, traversal = live_graph
    result = etf_overlap(client, PORTFOLIO, traversal, TODAY)
    by_etf = {row["etf_key"]: row for row in result.data}

    assert by_etf["SMH"]["overlap_count"] == 4
    assert all(row["overlap_count"] >= traversal.min_shared_positions for row in result.data)


def test_peer_group_returns_each_peer_once(live_graph) -> None:
    """AMD is both a declared competitor and a same-industry peer of NVDA."""
    client, _ = live_graph
    result = peer_group(client, "NVDA", 10, TODAY)
    keys = [row["peer_key"] for row in result.data]

    assert len(keys) == len(set(keys)), f"duplicate peers returned: {keys}"
    assert "NVDA" not in keys
    by_peer = {row["peer_key"]: row["basis"] for row in result.data}
    assert by_peer["AMD"] == "declared_competitor", "stronger basis must win"


def test_theme_exposure_aggregates_holdings_per_node(live_graph) -> None:
    client, traversal = live_graph
    result = theme_exposure(client, PORTFOLIO, traversal, TODAY)
    by_node = {row["node_key"]: row for row in result.data}

    assert by_node["ai-infrastructure"]["holding_count"] == len(PORTFOLIO)


def test_every_live_result_carries_provenance(live_graph) -> None:
    """A row without a source or as_of is a bug, per CLAUDE.md section 5."""
    client, traversal = live_graph
    for result in (
        company_relationships(client, "NVDA", traversal, TODAY),
        supply_chain(client, "NVDA", traversal, TODAY),
        hidden_concentration(client, PORTFOLIO, traversal, TODAY),
        data_freshness(client, TODAY),
    ):
        assert result.sources, f"{result.query} returned no sources"
        assert result.as_of == SEED_AS_OF, f"{result.query} lost its as_of"
        assert result.warnings == [], f"{result.query} warned unexpectedly: {result.warnings}"


def test_unknown_ticker_returns_an_explained_empty_result(live_graph) -> None:
    client, traversal = live_graph
    result = supply_chain(client, "NOSUCHTICKER", traversal, TODAY)

    assert result.data == []
    assert result.as_of is None
    assert "NOSUCHTICKER" in result.warnings[0]


def test_ingest_is_idempotent(live_graph) -> None:
    """Re-running a backfill must not duplicate nodes or edges."""
    client, _ = live_graph
    from seed_graph import build_edges, build_nodes

    def counts() -> tuple[int, int]:
        nodes = client.run("MATCH (n) RETURN count(n) AS c", {})[0]["c"]
        edges = client.run("MATCH ()-[r]->() RETURN count(r) AS c", {})[0]["c"]
        return nodes, edges

    before = counts()
    report = ingest(client, build_nodes(), build_edges())

    assert counts() == before
    assert report.skipped_edges == []

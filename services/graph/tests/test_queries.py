"""Query loading and the safety of structural placeholder substitution."""

from __future__ import annotations

import pytest

from graph_service.queries import (
    QUERY_DIR,
    QueryError,
    bind_query,
    load_query,
    split_statements,
)
from graph_service.schema import NodeLabel, RelType


def test_every_query_file_loads() -> None:
    names = sorted(path.stem for path in QUERY_DIR.glob("*.cypher"))
    assert names, "no Cypher files found"
    for name in names:
        assert load_query(name).strip()


def test_load_query_rejects_path_traversal() -> None:
    with pytest.raises(QueryError, match="bare identifier"):
        load_query("../../etc/passwd")


def test_load_query_reports_available_names_when_missing() -> None:
    with pytest.raises(QueryError, match="supply_chain"):
        load_query("no_such_query")


def test_bind_query_substitutes_label_and_keeps_values_as_parameters() -> None:
    bound = bind_query(
        "upsert_node",
        label=NodeLabel.COMPANY,
        key="NVDA",
        properties={"name": "NVIDIA"},
        source="fmp:profile",
        as_of="2026-09-05",
        confidence=1.0,
    )
    assert "MERGE (n:Company {key: $key})" in bound.cypher
    assert "$label" not in bound.cypher
    assert bound.parameters["key"] == "NVDA"
    assert "label" not in bound.parameters


def test_bind_query_substitutes_relationship_type() -> None:
    bound = bind_query(
        "upsert_edge",
        rel_type=RelType.SUPPLIES,
        start_label=NodeLabel.COMPANY,
        end_label=NodeLabel.COMPANY,
        start_key="TSM",
        end_key="NVDA",
        weight=0.6,
        properties={},
        source="sec:10-K",
        as_of="2026-09-05",
        confidence=0.9,
    )
    assert "[r:SUPPLIES]" in bound.cypher
    assert bound.parameters["weight"] == 0.6


def test_bind_query_substitutes_traversal_bound() -> None:
    bound = bind_query("supply_chain", ticker="NVDA", max_hops=3, min_weight=0.05)
    assert "[:SUPPLIES*1..3]" in bound.cypher
    assert "max_hops" not in bound.parameters


def test_bind_query_rejects_injected_label() -> None:
    with pytest.raises(QueryError, match="NodeLabel"):
        bind_query(
            "upsert_node",
            label="Company) DETACH DELETE (n",
            key="NVDA",
            properties={},
            source="x",
            as_of="2026-09-05",
            confidence=1.0,
        )


def test_bind_query_rejects_injected_relationship_type() -> None:
    with pytest.raises(QueryError, match="RelType"):
        bind_query(
            "upsert_edge",
            rel_type="SUPPLIES|*",
            start_label=NodeLabel.COMPANY,
            end_label=NodeLabel.COMPANY,
            start_key="TSM",
            end_key="NVDA",
            weight=0.6,
            properties={},
            source="x",
            as_of="2026-09-05",
            confidence=1.0,
        )


def test_bind_query_rejects_non_integer_bound() -> None:
    with pytest.raises(QueryError, match="must be an int"):
        bind_query("supply_chain", ticker="NVDA", max_hops="3", min_weight=0.05)


def test_bind_query_rejects_out_of_range_bound() -> None:
    with pytest.raises(QueryError, match=r"\[1, 10\]"):
        bind_query("supply_chain", ticker="NVDA", max_hops=99, min_weight=0.05)


def test_bind_query_rejects_missing_value() -> None:
    with pytest.raises(QueryError, match="needs values for"):
        bind_query("supply_chain", ticker="NVDA", max_hops=3)


def test_bind_query_rejects_unused_value() -> None:
    with pytest.raises(QueryError, match="does not use"):
        bind_query(
            "supply_chain", ticker="NVDA", max_hops=3, min_weight=0.05, stray=1
        )


def test_split_statements_drops_comments_and_semicolons() -> None:
    statements = split_statements(load_query("schema_constraints"))
    assert all(not s.startswith("//") for s in statements)
    assert all(";" not in s for s in statements)
    assert any("Company" in s and "UNIQUE" in s for s in statements)

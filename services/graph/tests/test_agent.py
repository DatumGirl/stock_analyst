"""The Graph agent's query surface: parameters passed and warnings raised."""

from __future__ import annotations

from datetime import date

from graph_service.agent import (
    STALE_AFTER_DAYS,
    company_relationships,
    data_freshness,
    etf_overlap,
    event_propagation,
    hidden_concentration,
    peer_group,
    supply_chain,
    theme_exposure,
)

TODAY = date(2026, 9, 5)
FRESH = "2026-08-01"
PORTFOLIO = ["NVDA", "AMD", "AVGO", "MU"]


def test_hidden_concentration_returns_shared_dependency(runner, traversal) -> None:
    runner.rows = [
        {
            "dependency_label": "Company",
            "dependency_key": "TSM",
            "affected_tickers": PORTFOLIO,
            "affected_count": 4,
            "total_exposure": 1.9,
            "sources": ["sec:10-K"],
            "as_of": FRESH,
        }
    ]
    result = hidden_concentration(runner, PORTFOLIO, traversal, today=TODAY)

    assert result.query == "hidden_concentration"
    assert result.data[0]["affected_count"] == 4
    assert result.sources == ["sec:10-K"]
    assert result.as_of == date(2026, 8, 1)
    assert result.warnings == []


def test_hidden_concentration_passes_thresholds_as_parameters(runner, traversal) -> None:
    hidden_concentration(runner, PORTFOLIO, traversal, today=TODAY)

    _, parameters = runner.calls[0]
    assert parameters["tickers"] == PORTFOLIO
    assert parameters["min_shared"] == traversal.min_shared_positions
    assert parameters["min_weight"] == traversal.min_exposure_weight
    assert "max_hops" not in parameters


def test_empty_result_explains_itself_rather_than_implying_no_risk(runner, traversal) -> None:
    result = hidden_concentration(runner, PORTFOLIO, traversal, today=TODAY)

    assert result.data == []
    assert result.warnings == ["no dependency is shared by multiple positions"]


def test_stale_data_raises_a_warning_naming_the_age(runner, traversal) -> None:
    stale_date = date(2026, 1, 5)
    runner.rows = [{"supplier_key": "TSM", "sources": ["sec:10-K"], "as_of_dates": [stale_date.isoformat()]}]
    result = supply_chain(runner, "NVDA", traversal, today=TODAY)

    assert result.as_of == stale_date
    assert len(result.warnings) == 1
    assert f"{(TODAY - stale_date).days} days old" in result.warnings[0]


def test_data_exactly_at_the_staleness_boundary_is_not_flagged(runner, traversal) -> None:
    from datetime import timedelta

    boundary = TODAY - timedelta(days=STALE_AFTER_DAYS)
    runner.rows = [{"supplier_key": "TSM", "source": "sec:10-K", "as_of": boundary.isoformat()}]
    result = supply_chain(runner, "NVDA", traversal, today=TODAY)

    assert result.warnings == []


def test_rows_without_dates_warn_that_freshness_is_unknown(runner, traversal) -> None:
    runner.rows = [{"supplier_key": "TSM"}]
    result = supply_chain(runner, "NVDA", traversal, today=TODAY)

    assert result.as_of is None
    assert "freshness as unknown" in result.warnings[0]


def test_supply_chain_avoids_the_reserved_word_hops(runner, traversal) -> None:
    """`hops` is reserved in Memgraph's grammar and fails to parse as a variable."""
    supply_chain(runner, "NVDA", traversal, today=TODAY)

    cypher, _ = runner.calls[0]
    assert " AS hops" not in cypher
    assert "hop_count" in cypher


def test_data_freshness_result_keeps_its_provenance(runner) -> None:
    runner.rows = [
        {"node_label": "Company", "node_count": 7, "oldest_as_of": FRESH, "sources": ["sec:10-K"]}
    ]
    result = data_freshness(runner, today=TODAY)

    assert result.as_of == date(2026, 8, 1)
    assert result.sources == ["sec:10-K"]
    assert result.warnings == []


def test_supply_chain_substitutes_hop_bound_into_the_pattern(runner, traversal) -> None:
    supply_chain(runner, "NVDA", traversal, today=TODAY)

    cypher, parameters = runner.calls[0]
    assert f"[:SUPPLIES*1..{traversal.max_hops}]" in cypher
    assert parameters["ticker"] == "NVDA"


def test_event_propagation_scopes_to_given_tickers(runner, traversal) -> None:
    event_propagation(runner, "news:tsmc-quake-2026", traversal, tickers=PORTFOLIO, today=TODAY)

    _, parameters = runner.calls[0]
    assert parameters["event_key"] == "news:tsmc-quake-2026"
    assert parameters["tickers"] == PORTFOLIO
    assert parameters["decay"] == traversal.propagation_decay


def test_event_propagation_without_tickers_passes_null_scope(runner, traversal) -> None:
    event_propagation(runner, "macro:fed-hike", traversal, today=TODAY)

    _, parameters = runner.calls[0]
    assert parameters["tickers"] is None


def test_etf_overlap_requires_the_shared_holding_threshold(runner, traversal) -> None:
    etf_overlap(runner, PORTFOLIO, traversal, today=TODAY)

    _, parameters = runner.calls[0]
    assert parameters["min_shared"] == traversal.min_shared_positions


def test_company_relationships_filters_by_exposure_floor(runner, traversal) -> None:
    company_relationships(runner, "NVDA", traversal, today=TODAY)

    _, parameters = runner.calls[0]
    assert parameters["min_weight"] == traversal.min_exposure_weight


def test_peer_group_applies_the_requested_limit(runner) -> None:
    peer_group(runner, "NVDA", limit=5, today=TODAY)

    _, parameters = runner.calls[0]
    assert parameters == {"ticker": "NVDA", "limit": 5}


def test_theme_exposure_aggregates_across_holdings(runner, traversal) -> None:
    runner.rows = [
        {
            "node_label": "Theme",
            "node_key": "ai-infrastructure",
            "holding_count": 3,
            "total_weight": 2.4,
            "sources": ["analyst:manual"],
            "as_of": FRESH,
        }
    ]
    result = theme_exposure(runner, PORTFOLIO, traversal, today=TODAY)

    assert result.data[0]["holding_count"] == 3
    assert result.warnings == []


def test_data_freshness_takes_no_parameters(runner) -> None:
    result = data_freshness(runner, today=TODAY)

    _, parameters = runner.calls[0]
    assert parameters == {}
    assert result.query == "data_freshness"


def test_result_is_json_serializable(runner, traversal) -> None:
    import json

    runner.rows = [{"dependency_key": "TSM", "source": "sec:10-K", "as_of": FRESH}]
    result = hidden_concentration(runner, PORTFOLIO, traversal, today=TODAY)

    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["as_of"] == FRESH
    assert payload["sources"] == ["sec:10-K"]

"""Provenance summarisation across scalar and path-aggregated rows."""

from __future__ import annotations

from datetime import date

from graph_service.results import GraphResult, summarize_provenance


def test_summarize_returns_empty_for_no_rows() -> None:
    assert summarize_provenance([]) == ([], None)


def test_summarize_collects_scalar_provenance() -> None:
    rows = [
        {"source": "sec:10-K", "as_of": "2026-06-30"},
        {"source": "fmp:etf", "as_of": "2026-08-01"},
    ]
    sources, as_of = summarize_provenance(rows)
    assert sources == ["fmp:etf", "sec:10-K"]
    assert as_of == date(2026, 6, 30)


def test_summarize_flattens_path_aggregated_provenance() -> None:
    rows = [{"sources": ["sec:10-K", "sec:10-Q"], "as_of_dates": ["2026-07-01", "2026-05-02"]}]
    sources, as_of = summarize_provenance(rows)
    assert sources == ["sec:10-K", "sec:10-Q"]
    assert as_of == date(2026, 5, 2)


def test_summarize_flattens_nested_source_lists() -> None:
    rows = [{"sources": [["sec:10-K"], ["fmp:etf", "sec:10-K"]]}]
    sources, _ = summarize_provenance(rows)
    assert sources == ["fmp:etf", "sec:10-K"]


def test_summarize_ignores_unparseable_dates() -> None:
    rows = [{"as_of": "not-a-date", "source": "manual"}]
    sources, as_of = summarize_provenance(rows)
    assert sources == ["manual"]
    assert as_of is None


def test_summarize_reads_the_oldest_as_of_key_from_aggregate_rows() -> None:
    """data_freshness reports bounds as oldest_as_of, not as_of."""
    rows = [
        {"node_label": "Company", "oldest_as_of": "2026-06-30", "sources": ["sec:10-K"]},
        {"node_label": "ETF", "oldest_as_of": "2026-02-01", "sources": ["provider:etf"]},
    ]
    sources, as_of = summarize_provenance(rows)
    assert as_of == date(2026, 2, 1)
    assert sources == ["provider:etf", "sec:10-K"]


def test_summarize_accepts_native_date_objects() -> None:
    rows = [{"as_of": date(2026, 4, 1), "source": "manual"}]
    _, as_of = summarize_provenance(rows)
    assert as_of == date(2026, 4, 1)


def test_result_serializes_as_of_to_iso_string() -> None:
    result = GraphResult(query="supply_chain", as_of=date(2026, 3, 2))
    assert result.to_dict()["as_of"] == "2026-03-02"


def test_result_serializes_missing_as_of_to_none() -> None:
    assert GraphResult(query="supply_chain").to_dict()["as_of"] is None

"""The Graph agent's query surface — the tools the Chief Analyst calls.

Each function answers one relationship question and returns a
:class:`GraphResult`. None of them interpret, rank by attractiveness, or
recommend; they return structured evidence with provenance and let the Chief
Analyst reason over it.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from .client import QueryRunner, run_bound
from .config import TraversalSettings
from .queries import bind_query
from .results import GraphResult, summarize_provenance

#: A relationship fact older than this is flagged; supply-chain and index
#: membership disclosures update on a roughly quarterly filing cadence.
STALE_AFTER_DAYS = 120
DEFAULT_PEER_LIMIT = 10


def company_relationships(
    runner: QueryRunner,
    ticker: str,
    settings: TraversalSettings,
    today: date | None = None,
) -> GraphResult:
    """Return a company's direct suppliers, customers, competitors and themes.

    Args:
        runner: Execution surface to query through.
        ticker: The company's natural key.
        settings: Traversal limits, of which the exposure floor is used.
        today: Reference date for staleness; defaults to the current UTC date.

    Returns:
        One row per neighbouring node with relationship type, direction and weight.
    """
    query = bind_query(
        "company_relationships",
        ticker=ticker,
        min_weight=settings.min_exposure_weight,
    )
    rows = run_bound(runner, query)
    return _build_result("company_relationships", rows, today, empty_note=f"no relationships recorded for {ticker!r}")


def supply_chain(
    runner: QueryRunner,
    ticker: str,
    settings: TraversalSettings,
    today: date | None = None,
) -> GraphResult:
    """Return the multi-hop upstream supply chain with cumulative exposure.

    Args:
        runner: Execution surface to query through.
        ticker: The company whose suppliers to trace.
        settings: Traversal depth and the exposure floor below which a path is noise.
        today: Reference date for staleness; defaults to the current UTC date.

    Returns:
        One row per upstream supplier with hop count and cumulative weight.
    """
    query = bind_query(
        "supply_chain",
        ticker=ticker,
        max_hops=settings.max_hops,
        min_weight=settings.min_exposure_weight,
    )
    rows = run_bound(runner, query)
    return _build_result("supply_chain", rows, today, empty_note=f"no supply-chain relationships recorded for {ticker!r}")


def etf_overlap(
    runner: QueryRunner,
    tickers: list[str],
    settings: TraversalSettings,
    today: date | None = None,
) -> GraphResult:
    """Return ETFs holding more than one of the given tickers.

    Args:
        runner: Execution surface to query through.
        tickers: Holdings to test for shared index membership.
        settings: Supplies the overlap threshold and the weight floor.
        today: Reference date for staleness; defaults to the current UTC date.

    Returns:
        One row per overlapping ETF with the tickers it holds in common.
    """
    query = bind_query(
        "etf_overlap",
        tickers=tickers,
        min_weight=settings.min_exposure_weight,
        min_shared=settings.min_shared_positions,
    )
    rows = run_bound(runner, query)
    return _build_result("etf_overlap", rows, today, empty_note="no ETF holds more than one of these positions")


def hidden_concentration(
    runner: QueryRunner,
    tickers: list[str],
    settings: TraversalSettings,
    today: date | None = None,
) -> GraphResult:
    """Return dependencies shared by several holdings through indirect paths.

    This is the evidence behind "four positions share semiconductor supply-chain
    risk": concentration that sector allocation alone does not reveal.

    Args:
        runner: Execution surface to query through.
        tickers: The portfolio's holdings.
        settings: Traversal depth, the shared-position threshold and weight floor.
        today: Reference date for staleness; defaults to the current UTC date.

    Returns:
        One row per shared dependency with the affected tickers and exposures.
    """
    query = bind_query(
        "hidden_concentration",
        tickers=tickers,
        max_hops=settings.max_hops,
        min_weight=settings.min_exposure_weight,
        min_shared=settings.min_shared_positions,
    )
    rows = run_bound(runner, query)
    return _build_result("hidden_concentration", rows, today, empty_note="no dependency is shared by multiple positions")


def event_propagation(
    runner: QueryRunner,
    event_key: str,
    settings: TraversalSettings,
    tickers: list[str] | None = None,
    today: date | None = None,
) -> GraphResult:
    """Trace which companies an event reaches, attenuated by distance.

    Args:
        runner: Execution surface to query through.
        event_key: Natural key of the news or macro event.
        settings: Traversal depth, per-hop decay and the impact floor.
        tickers: Restrict results to these companies; ``None`` returns all reached.
        today: Reference date for staleness; defaults to the current UTC date.

    Returns:
        One row per affected company with hop count, path and impact score.
    """
    query = bind_query(
        "event_propagation",
        event_key=event_key,
        max_hops=settings.max_hops,
        min_weight=settings.min_exposure_weight,
        decay=settings.propagation_decay,
        tickers=tickers,
    )
    rows = run_bound(runner, query)
    return _build_result("event_propagation", rows, today, empty_note=f"event {event_key!r} reaches no company above the impact floor")


def peer_group(
    runner: QueryRunner,
    ticker: str,
    limit: int = DEFAULT_PEER_LIMIT,
    today: date | None = None,
) -> GraphResult:
    """Return declared competitors and same-industry peers for comparison.

    Args:
        runner: Execution surface to query through.
        ticker: The company whose peers to fetch.
        limit: Maximum peers to return.
        today: Reference date for staleness; defaults to the current UTC date.

    Returns:
        One row per peer with the basis on which it qualified.
    """
    query = bind_query("peer_group", ticker=ticker, limit=limit)
    rows = run_bound(runner, query)
    return _build_result("peer_group", rows, today, empty_note=f"no peers recorded for {ticker!r}")


def theme_exposure(
    runner: QueryRunner,
    tickers: list[str],
    settings: TraversalSettings,
    today: date | None = None,
) -> GraphResult:
    """Return theme and geography exposure aggregated across holdings.

    Weights are relationship strengths only; position sizes live in Postgres and
    are joined by the Portfolio agent.

    Args:
        runner: Execution surface to query through.
        tickers: The holdings to aggregate.
        settings: Supplies the weight floor.
        today: Reference date for staleness; defaults to the current UTC date.

    Returns:
        One row per theme or country with contributing holdings.
    """
    query = bind_query(
        "theme_exposure",
        tickers=tickers,
        min_weight=settings.min_exposure_weight,
    )
    rows = run_bound(runner, query)
    return _build_result("theme_exposure", rows, today, empty_note="no theme or geography relationships recorded for these positions")


def data_freshness(runner: QueryRunner, today: date | None = None) -> GraphResult:
    """Return per-label node counts and the oldest and newest ``as_of``.

    Args:
        runner: Execution surface to query through.
        today: Reference date for staleness; defaults to the current UTC date.

    Returns:
        One row per node label describing how current that slice of the graph is.
    """
    query = bind_query("data_freshness")
    rows = run_bound(runner, query)
    return _build_result("data_freshness", rows, today, empty_note="the graph holds no provenanced nodes")


def _build_result(
    query_name: str,
    rows: list[dict[str, Any]],
    today: date | None,
    empty_note: str,
) -> GraphResult:
    """Wrap query rows in the agent envelope, adding emptiness and staleness warnings.

    Args:
        query_name: Name of the query answered.
        rows: Rows the query returned.
        today: Reference date for staleness; defaults to the current UTC date.
        empty_note: Warning to attach when no rows matched, so an empty answer
            is explained rather than read as "no risk".

    Returns:
        The populated result envelope.
    """
    reference_date = today or datetime.now(timezone.utc).date()
    sources, as_of = summarize_provenance(rows)
    warnings: list[str] = []
    if not rows:
        warnings.append(empty_note)
    if as_of is None and rows:
        warnings.append(f"{query_name} rows carry no as_of date; treat freshness as unknown")
    elif as_of is not None:
        age_days = (reference_date - as_of).days
        if age_days > STALE_AFTER_DAYS:
            warnings.append(
                f"oldest relationship data is {age_days} days old "
                f"(as of {as_of.isoformat()}), beyond the {STALE_AFTER_DAYS}-day refresh window"
            )
    return GraphResult(
        query=query_name,
        data=rows,
        sources=sources,
        as_of=as_of,
        warnings=warnings,
    )

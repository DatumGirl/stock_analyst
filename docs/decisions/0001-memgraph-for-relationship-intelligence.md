# ADR 0001 — Memgraph for relationship intelligence

- **Status:** Accepted
- **Date:** 2026-09-05
- **Phase:** 5 (Graph intelligence)

## Context

Analysing a company in isolation misses the risk that matters most to a
portfolio. Four holdings can look diversified by sector while depending on the
same foundry, the same country, or the same theme. Answering "which of my
positions does this event actually reach?" requires traversing supplier,
customer, competitor, ETF, geography and theme relationships to arbitrary depth.

Postgres is the system of record and already holds prices, fundamentals and user
portfolios. Expressing multi-hop traversal there means recursive CTEs that are
hard to read, hard to tune, and awkward to vary by relationship type.

## Decision

Use **Memgraph** as a dedicated relationship store, queried through GQLAlchemy
from `services/graph`, exposed to the orchestrator as the Graph agent.

Scope boundaries, following CLAUDE.md section 2:

- The graph stores **relationships only**. No time-series, no user data, no
  positions. Position sizes stay in Postgres and are joined by the Portfolio
  agent against graph weights.
- The graph returns **evidence, not conclusions**. It computes exposure and
  impact scores from stored edge weights; interpretation belongs to the Chief
  Analyst.
- Every node and edge carries `source` and `as_of`. Ingestion validates
  provenance before writing, so an unauditable fact cannot enter the graph.

Cypher lives in `services/graph/queries/` as files, not inline strings, so the
queries are reviewable and testable independently of the Python that calls them.

## Consequences

**Positive**

- Multi-hop questions are expressed directly. Hidden concentration, event
  propagation and supply-chain depth are one query each.
- Traversal direction can vary per relationship type, which matters: a supplier
  disruption propagates downstream to customers, not upstream.
- The service is testable without a database — the `QueryRunner` protocol lets
  unit tests stub execution — while integration tests exercise the real Cypher.

**Negative**

- A second datastore to operate, back up and monitor.
- The graph can disagree with Postgres about which tickers exist. Ingestion
  treats Postgres as authoritative and skips edges whose endpoints are absent
  rather than creating unprovenanced nodes.
- Relationship data is inherently staler than price data. Results carry an
  `as_of` and warn beyond a 120-day refresh window so the UI can mark it.

## Alternatives considered

- **Recursive CTEs in Postgres** — no new infrastructure, but multi-hop queries
  with per-type direction and weight decay become unreadable, and the traversal
  cost lands on the system of record.
- **Neo4j** — comparable query model and a larger ecosystem; Memgraph was chosen
  for its in-memory performance profile on a graph of this size and its
  Cypher compatibility, which keeps the queries portable if that changes.

## Notes for implementers

Two constraints were found by running the queries against a real instance and
are easy to reintroduce:

- `hops` is a reserved word in Memgraph's grammar; the queries use `hop_count`.
- Labels, relationship types and variable-length bounds cannot be query
  parameters. `graph_service.queries.bind_query` substitutes them textually
  after validating against the schema enums; never interpolate them by hand.

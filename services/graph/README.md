# services/graph — relationship intelligence

Memgraph-backed relationship store and the Graph agent's query surface.

The graph answers questions that per-company analysis cannot: *which of my
positions share a dependency they don't appear to share?* and *which holdings
does this event actually reach, and how hard?*

It stores **relationships only**. Prices, fundamentals and portfolios live in
Postgres; position sizes are joined against graph weights by the Portfolio
agent. See [ADR 0001](../../docs/decisions/0001-memgraph-for-relationship-intelligence.md).

## Layout

```
graph_service/
  schema.py     node labels, relationship types, provenance contract
  config.py     environment-driven settings; fails loudly when unset
  queries.py    loads queries/*.cypher and binds them safely
  client.py     the only I/O boundary (GQLAlchemy)
  ingest.py     validate-then-write, idempotent upserts
  agent.py      the eight tools the Chief Analyst calls
  results.py    the {data, sources, as_of, warnings} envelope
queries/        Cypher, one file per question
scripts/        seed_graph.py — development fixture data
tests/          unit tests (no database) + live integration tests
```

## Model

Nodes: `Company`, `Sector`, `Industry`, `ETF`, `Country`, `Commodity`,
`Technology`, `Theme`, `RiskFactor`, `NewsEvent`, `MacroEvent`.

Relationships: `SUPPLIES`, `CUSTOMER_OF`, `COMPETES_WITH`, `IN_SECTOR`,
`IN_INDUSTRY`, `HELD_BY`, `OPERATES_IN`, `DEPENDS_ON`, `EXPOSED_TO`,
`PART_OF_THEME`, `AFFECTS`.

Nodes are keyed by a natural `key` unique within their label. Edges expressing
an exposure fraction (`SUPPLIES`, `CUSTOMER_OF`, `HELD_BY`, `OPERATES_IN`,
`DEPENDS_ON`) require a `weight` in [0, 1]; ingestion rejects them without one.

Every node and edge carries `source` and `as_of`. A fact without provenance is
rejected at ingestion, not stored and flagged later.

## Queries

| Query | Answers |
|---|---|
| `company_relationships` | Who is this company directly connected to? |
| `supply_chain` | Who supplies it, and its suppliers, with cumulative exposure |
| `etf_overlap` | Which ETFs hold more than one of these positions? |
| `hidden_concentration` | Which dependency do several holdings share? |
| `event_propagation` | Which companies does this event reach, and how hard? |
| `peer_group` | Defensible comparison set for `/compare` |
| `theme_exposure` | Theme and geography exposure across holdings |
| `data_freshness` | How current is each slice of the graph? |

Each returns a `GraphResult` with `data`, `sources`, `as_of` and `warnings`.
An empty result always carries a warning explaining *why* it is empty, so
"nothing found" is never read as "no risk". Data older than 120 days is flagged.

## Local development

```bash
cp .env.example .env.local          # then fill in credentials
set -a && source .env.local && set +a

docker compose up -d                # Memgraph on $MEMGRAPH_PORT
python scripts/seed_graph.py        # schema + fixture graph
pytest                              # unit + live integration tests
mypy --strict graph_service
```

`pytest` runs without a database — live tests skip unless `MEMGRAPH_PASSWORD`
is set and the instance is reachable. Run them: the Cypher's real failure modes
(parse errors, reserved words, traversal direction) are invisible to tests that
stub the driver.

## Extending

**A new query:** add `queries/<name>.cypher`, then a function in `agent.py` that
binds it and wraps the rows via `_build_result`. Cover it in
`tests/test_live_memgraph.py` — a query that only has unit tests is unverified.

**A new relationship type:** add it to `RelType`, add it to
`FRACTIONAL_REL_TYPES` if its weight is an exposure fraction, and add a
uniqueness constraint for any new label in `queries/schema_constraints.cypher`.

## Constraints worth knowing

- `hops` is reserved in Memgraph's grammar — the queries use `hop_count`.
- Labels, relationship types and variable-length bounds **cannot** be query
  parameters. `bind_query` substitutes them textually after validating against
  the schema enums. Never interpolate them by hand; that is a Cypher injection.
- Propagation direction varies by relationship type. Disruption at a supplier
  flows *downstream* to the companies it supplies.

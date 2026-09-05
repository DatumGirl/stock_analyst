// Theme and geography exposure across a set of holdings, aggregated by node.
// The Portfolio agent joins these weights against position sizes in Postgres;
// the graph never sees quantities or cost basis.
MATCH (c:Company)-[r:PART_OF_THEME|OPERATES_IN]->(node)
WHERE c.key IN $tickers AND coalesce(r.weight, 1.0) >= $min_weight
RETURN labels(node)[0] AS node_label,
       node.key AS node_key,
       node.name AS node_name,
       collect({ticker: c.key, weight: coalesce(r.weight, 1.0)}) AS holdings,
       count(DISTINCT c) AS holding_count,
       sum(coalesce(r.weight, 1.0)) AS total_weight,
       collect(DISTINCT r.source) AS sources,
       max(r.as_of) AS as_of
ORDER BY holding_count DESC, total_weight DESC, node_key;

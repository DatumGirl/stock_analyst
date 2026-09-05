// Multi-hop supply chain traversal.
// Note: 'hops' is a reserved word in Memgraph — use hop_count (ADR 0001).
// Max hops is substituted by bind_query before execution.
// Parameter: $symbol (string)
MATCH path = (c:Company {symbol: $symbol})-[:SUPPLIES*1..{{MAX_HOPS}}]->(upstream:Company)
WITH c, upstream, length(path) AS hop_count,
     reduce(w = 1.0, r IN relationships(path) | w * r.weight) AS chain_weight
WHERE chain_weight > 0.05
RETURN upstream.symbol AS symbol,
       upstream.name AS name,
       hop_count,
       chain_weight,
       upstream.source AS source,
       upstream.as_of AS as_of
ORDER BY hop_count ASC, chain_weight DESC

// Direct one-hop neighbourhood of a company: suppliers, customers, competitors,
// sector/industry, ETF membership, geography, dependencies, themes, risks.
// Used by the Graph agent to answer "who is this company connected to?".
MATCH (c:Company {key: $ticker})-[r]-(neighbor)
WHERE type(r) <> 'AFFECTS'
  AND (r.weight IS NULL OR r.weight >= $min_weight)
RETURN type(r) AS rel_type,
       startNode(r).key = $ticker AS is_outgoing,
       labels(neighbor)[0] AS neighbor_label,
       neighbor.key AS neighbor_key,
       neighbor.name AS neighbor_name,
       r.weight AS weight,
       r.source AS source,
       r.as_of AS as_of,
       r.confidence AS confidence
ORDER BY coalesce(r.weight, 0) DESC, neighbor.key;

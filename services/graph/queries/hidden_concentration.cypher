// Dependencies shared by several portfolio positions through indirect paths.
// This is the "37% tech, but four positions share semiconductor supply-chain
// risk" query: it finds the shared node, not the shared sector label.
// Note: `hops` is reserved in Memgraph's grammar, hence `hop_count`.
MATCH path = (c:Company)-[:SUPPLIES|DEPENDS_ON|OPERATES_IN|PART_OF_THEME|EXPOSED_TO*1..$max_hops]->(dependency)
WHERE c.key IN $tickers
  AND NOT dependency.key IN $tickers
  AND all(r IN relationships(path) WHERE coalesce(r.weight, 1.0) >= $min_weight)
WITH dependency,
     c.key AS ticker,
     min(size(relationships(path))) AS hop_count,
     max(reduce(w = 1.0, r IN relationships(path) | w * coalesce(r.weight, 1.0))) AS exposure,
     collect([r IN relationships(path) | r.source]) AS path_sources,
     max([r IN relationships(path) | r.as_of][0]) AS path_as_of
WITH dependency,
     collect({ticker: ticker, hop_count: hop_count, exposure: exposure}) AS exposures,
     collect(DISTINCT ticker) AS tickers,
     sum(exposure) AS total_exposure,
     collect(path_sources) AS sources,
     max(path_as_of) AS as_of
WHERE size(tickers) >= $min_shared
RETURN labels(dependency)[0] AS dependency_label,
       dependency.key AS dependency_key,
       dependency.name AS dependency_name,
       tickers AS affected_tickers,
       size(tickers) AS affected_count,
       exposures,
       total_exposure,
       sources,
       as_of
ORDER BY affected_count DESC, total_exposure DESC, dependency_key;

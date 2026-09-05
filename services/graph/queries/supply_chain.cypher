// Multi-hop upstream supply chain for a company, with cumulative exposure.
// Cumulative weight is the product of edge weights along the path, so a weak
// link upstream correctly dilutes the exposure it transmits downstream.
// Note: `hops` is reserved in Memgraph's grammar, hence `hop_count`.
MATCH path = (c:Company {key: $ticker})<-[:SUPPLIES*1..$max_hops]-(supplier:Company)
WITH supplier,
     size(relationships(path)) AS hop_count,
     reduce(w = 1.0, r IN relationships(path) | w * coalesce(r.weight, 0.0)) AS cumulative_weight,
     [r IN relationships(path) | r.source] AS path_sources,
     [r IN relationships(path) | r.as_of] AS path_as_of
WHERE cumulative_weight >= $min_weight
RETURN supplier.key AS supplier_key,
       supplier.name AS supplier_name,
       min(hop_count) AS hop_count,
       max(cumulative_weight) AS cumulative_weight,
       collect(path_sources) AS sources,
       collect(path_as_of) AS as_of_dates
ORDER BY cumulative_weight DESC, supplier_key;

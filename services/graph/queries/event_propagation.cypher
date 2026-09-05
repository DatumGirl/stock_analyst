// Propagate a news or macro event outward from the entities it directly hits,
// attenuating impact by $decay per hop. Answers "this event landed on TSMC —
// which of my positions does it actually reach, and how hard?".
//
// Direction matters: disruption at a supplier flows DOWNSTREAM to the companies
// it supplies, so SUPPLIES is traversed with the arrow (origin)<-[:SUPPLIES]-()
// reversed relative to the other types. Shared dependencies (DEPENDS_ON,
// PART_OF_THEME, EXPOSED_TO) and peer effects (COMPETES_WITH, CUSTOMER_OF)
// are traversed undirected, since impact travels either way along them.
// Note: `hops` is reserved in Memgraph's grammar, hence `hop_count`.
MATCH (event {key: $event_key})-[a:AFFECTS]->(origin)
MATCH path = (origin)-[:SUPPLIES|CUSTOMER_OF|DEPENDS_ON|PART_OF_THEME|COMPETES_WITH|EXPOSED_TO*0..$max_hops]-(affected:Company)
WHERE $tickers IS NULL OR affected.key IN $tickers
WITH affected,
     origin,
     size(relationships(path)) AS hop_count,
     coalesce(a.weight, 1.0) AS origin_impact,
     reduce(w = 1.0, r IN relationships(path) | w * coalesce(r.weight, 1.0)) AS path_weight,
     event.source AS source,
     event.as_of AS as_of
WITH affected,
     collect(DISTINCT origin.key) AS via,
     max(origin_impact * path_weight * ($decay ^ hop_count)) AS impact_score,
     min(hop_count) AS hop_count,
     collect(DISTINCT source) AS sources,
     max(as_of) AS as_of
WHERE impact_score >= $min_weight
RETURN affected.key AS ticker,
       affected.name AS name,
       hop_count,
       via,
       impact_score,
       sources,
       as_of
ORDER BY impact_score DESC, ticker;

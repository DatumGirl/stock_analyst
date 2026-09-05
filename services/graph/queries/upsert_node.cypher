// Idempotent node upsert. Provenance is always overwritten so the newest
// assertion wins, and first_seen_at records when the node entered the graph.
MERGE (n:$label {key: $key})
ON CREATE SET n.first_seen_at = $as_of
SET n += $properties,
    n.source = $source,
    n.as_of = $as_of,
    n.confidence = $confidence
RETURN n.key AS key;

// Idempotent relationship upsert between two existing nodes.
// Both endpoints must already exist; a missing endpoint yields no rows, which
// the client surfaces as a warning rather than silently creating a bare node.
MATCH (start:$start_label {key: $start_key})
MATCH (end:$end_label {key: $end_key})
MERGE (start)-[r:$rel_type]->(end)
ON CREATE SET r.first_seen_at = $as_of
SET r += $properties,
    r.weight = $weight,
    r.source = $source,
    r.as_of = $as_of,
    r.confidence = $confidence
RETURN start.key AS start_key, end.key AS end_key;

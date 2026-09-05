// Per-label node counts and as_of bounds, so every graph answer can state how
// current the underlying relationship data is.
MATCH (n)
WHERE n.as_of IS NOT NULL
RETURN labels(n)[0] AS node_label,
       count(n) AS node_count,
       min(n.as_of) AS oldest_as_of,
       max(n.as_of) AS newest_as_of,
       collect(DISTINCT n.source) AS sources
ORDER BY node_label;

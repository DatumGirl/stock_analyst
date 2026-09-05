// Theme exposure for a list of tickers.
// Parameter: $symbols (list of strings)
MATCH (c:Company) WHERE c.symbol IN $symbols
MATCH (c)-[r:EXPOSED_TO_THEME]->(t:Theme)
RETURN c.symbol AS ticker, t.name AS theme, r.weight AS weight, r.as_of AS as_of
ORDER BY weight DESC

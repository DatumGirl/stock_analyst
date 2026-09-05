// Hidden concentration across a portfolio of tickers.
// Parameter: $symbols (list of strings)
MATCH (c:Company) WHERE c.symbol IN $symbols
MATCH (c)-[:EXPOSED_TO_THEME]->(t:Theme)
WITH t.name AS dependency, collect(DISTINCT c.symbol) AS exposed_tickers, count(DISTINCT c) AS ticker_count
WHERE ticker_count >= 2
RETURN dependency, exposed_tickers, ticker_count, 'theme' AS dependency_type
UNION ALL
MATCH (c:Company) WHERE c.symbol IN $symbols
MATCH (c)-[:EXPOSED_TO_COUNTRY]->(co:Country)
WITH co.name AS dependency, collect(DISTINCT c.symbol) AS exposed_tickers, count(DISTINCT c) AS ticker_count
WHERE ticker_count >= 2
RETURN dependency, exposed_tickers, ticker_count, 'country' AS dependency_type
UNION ALL
MATCH (c:Company) WHERE c.symbol IN $symbols
MATCH (c)-[:SUPPLIES]->(supplier:Company)
WITH supplier.name AS dependency, collect(DISTINCT c.symbol) AS exposed_tickers, count(DISTINCT c) AS ticker_count
WHERE ticker_count >= 2
RETURN dependency, exposed_tickers, ticker_count, 'supplier' AS dependency_type
ORDER BY ticker_count DESC

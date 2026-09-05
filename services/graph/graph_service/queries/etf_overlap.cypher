// ETFs that contain multiple portfolio tickers.
// Parameter: $symbols (list of strings)
MATCH (c:Company) WHERE c.symbol IN $symbols
MATCH (c)-[r:PART_OF_ETF]->(e:ETF)
WITH e.symbol AS etf_symbol,
     e.name AS etf_name,
     collect(DISTINCT c.symbol) AS member_tickers,
     count(DISTINCT c) AS member_count,
     avg(r.weight) AS avg_weight
WHERE member_count >= 2
RETURN etf_symbol, etf_name, member_tickers, member_count, avg_weight
ORDER BY member_count DESC, avg_weight DESC

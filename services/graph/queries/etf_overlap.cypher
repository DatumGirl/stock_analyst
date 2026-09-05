// ETFs that hold more than one of the given tickers, and the portfolio holdings
// they overlap on. Surfaces the passive-flow channel that links positions the
// user believes are independent.
MATCH (c:Company)-[h:HELD_BY]->(etf:ETF)
WHERE c.key IN $tickers AND h.weight >= $min_weight
WITH etf,
     collect(DISTINCT c.key) AS overlapping_tickers,
     sum(h.weight) AS combined_weight,
     collect(DISTINCT h.source) AS sources,
     max(h.as_of) AS as_of
WHERE size(overlapping_tickers) >= $min_shared
RETURN etf.key AS etf_key,
       etf.name AS etf_name,
       overlapping_tickers,
       size(overlapping_tickers) AS overlap_count,
       combined_weight,
       sources,
       as_of
ORDER BY overlap_count DESC, combined_weight DESC, etf_key;

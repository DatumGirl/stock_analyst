// Direct relationships for a company.
// Parameter: $symbol (string)
MATCH (c:Company {symbol: $symbol})
OPTIONAL MATCH (c)-[r1:SUPPLIES]->(supplier:Company)
OPTIONAL MATCH (c)<-[r2:IS_CUSTOMER_OF]-(customer:Company)
OPTIONAL MATCH (c)-[r3:COMPETES_WITH]->(competitor:Company)
OPTIONAL MATCH (c)-[r4:EXPOSED_TO_THEME]->(theme:Theme)
OPTIONAL MATCH (c)-[r5:EXPOSED_TO_COUNTRY]->(country:Country)
OPTIONAL MATCH (c)-[r6:PART_OF_ETF]->(etf:ETF)
WITH c,
  collect(DISTINCT {type: 'SUPPLIES', target: supplier.symbol, name: supplier.name, weight: r1.weight, direction: 'upstream', as_of: r1.as_of}) AS suppliers,
  collect(DISTINCT {type: 'IS_CUSTOMER_OF', target: customer.symbol, name: customer.name, weight: r2.weight, direction: 'downstream', as_of: r2.as_of}) AS customers,
  collect(DISTINCT {type: 'COMPETES_WITH', target: competitor.symbol, name: competitor.name, weight: r3.weight, direction: 'lateral', as_of: r3.as_of}) AS competitors,
  collect(DISTINCT {type: 'EXPOSED_TO_THEME', target: null, name: theme.name, weight: r4.weight, direction: 'lateral', as_of: r4.as_of}) AS themes,
  collect(DISTINCT {type: 'EXPOSED_TO_COUNTRY', target: null, name: country.name, weight: r5.weight, direction: 'lateral', as_of: r5.as_of}) AS countries,
  collect(DISTINCT {type: 'PART_OF_ETF', target: etf.symbol, name: etf.name, weight: r6.weight, direction: 'lateral', as_of: r6.as_of}) AS etfs
RETURN c.symbol AS symbol,
       suppliers + customers + competitors + themes + countries + etfs AS relationships

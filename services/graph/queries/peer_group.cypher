// Competitor set for a company: declared competitors plus same-industry peers,
// so /compare has a defensible peer group rather than a hand-picked one.
// The UNION collects both bases; the outer aggregation keeps one row per peer,
// preferring the declared-competitor basis (rank 0) over same-industry (rank 1).
CALL {
  MATCH (:Company {key: $ticker})-[comp:COMPETES_WITH]-(peer:Company)
  RETURN peer AS peer, 'declared_competitor' AS basis, 0 AS basis_rank,
         comp.weight AS weight, comp.source AS source, comp.as_of AS as_of
  UNION
  MATCH (:Company {key: $ticker})-[:IN_INDUSTRY]->(:Industry)<-[ind:IN_INDUSTRY]-(peer:Company)
  WHERE peer.key <> $ticker
  RETURN peer AS peer, 'same_industry' AS basis, 1 AS basis_rank,
         null AS weight, ind.source AS source, ind.as_of AS as_of
}
WITH peer, basis, basis_rank, weight, source, as_of
ORDER BY basis_rank
WITH peer,
     head(collect(basis)) AS basis,
     min(basis_rank) AS basis_rank,
     head(collect(weight)) AS weight,
     head(collect(source)) AS source,
     head(collect(as_of)) AS as_of
RETURN peer.key AS peer_key,
       peer.name AS peer_name,
       basis,
       weight,
       source,
       as_of
ORDER BY basis_rank, peer_key
LIMIT $limit;

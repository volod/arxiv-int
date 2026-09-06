-- arxiv-int AGE projection for domain-artifacts-supply-chain
LOAD 'age';
SET search_path = ag_catalog, '$user', public;
-- SELECT * FROM cypher('arxiv_int', $$ MATCH (a {id: row.from_object_id}), (b {id: row.to_object_id}) CREATE (a)-[:SUPPLY]->(b) $$) AS (e agtype);

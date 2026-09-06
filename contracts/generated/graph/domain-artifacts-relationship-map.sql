-- arxiv-int AGE projection for domain-artifacts-relationship-map
LOAD 'age';
SET search_path = ag_catalog, '$user', public;
-- SELECT * FROM cypher('arxiv_int', $$ MATCH (a {id: row.subject_object_id}), (b {id: row.object_object_id}) CREATE (a)-[:RELATIONSHIP]->(b) $$) AS (e agtype);

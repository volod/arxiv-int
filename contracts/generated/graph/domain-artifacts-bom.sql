-- arxiv-int AGE projection for domain-artifacts-bom
LOAD 'age';
SET search_path = ag_catalog, '$user', public;
-- SELECT * FROM cypher('arxiv_int', $$ MATCH (a {id: row.child_object_id}), (b {id: row.parent_object_id}) CREATE (a)-[:PART_OF]->(b) $$) AS (e agtype);

-- arxiv-int AGE projection for objects
LOAD 'age';
SET search_path = ag_catalog, '$user', public;
-- SELECT * FROM cypher('arxiv_int', $$ CREATE (:Object {id: row.object_id}) $$) AS (v agtype);
-- source table: kg.objects

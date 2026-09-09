-- arxiv-int AGE projection for domain-artifacts-invoice-payment
LOAD 'age';
SET search_path = ag_catalog, '$user', public;
-- SELECT * FROM cypher('arxiv_int', $$ MATCH (a {id: row.payment_object_id}), (b {id: row.invoice_object_id}) CREATE (a)-[:ALLOCATES]->(b) $$) AS (e agtype);

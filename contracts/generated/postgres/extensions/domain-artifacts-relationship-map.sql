-- arxiv-int postgres extensions for domain-artifacts-relationship-map
-- source: urn:arxiv-int:contract:domain-artifacts-relationship-map:1.0.0@1.0.0
ALTER TABLE kg.relationship_edges ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.relationship_edges USING (bucket)
-- CREATE TABLE kg.relationship_edges_p0 PARTITION OF kg.relationship_edges FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.relationship_edges ALTER COLUMN edge_id TYPE text;

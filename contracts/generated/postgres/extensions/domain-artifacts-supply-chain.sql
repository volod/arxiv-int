-- arxiv-int postgres extensions for domain-artifacts-supply-chain
-- source: urn:arxiv-int:contract:domain-artifacts-supply-chain:1.0.0@1.0.0
ALTER TABLE kg.supply_chain_edges ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.supply_chain_edges USING (bucket)
-- CREATE TABLE kg.supply_chain_edges_p0 PARTITION OF kg.supply_chain_edges FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.supply_chain_edges ALTER COLUMN edge_id TYPE text;

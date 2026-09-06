-- arxiv-int postgres extensions for facts
-- source: urn:arxiv-int:contract:facts:1.0.0@1.0.0
ALTER TABLE kg.facts ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.facts USING (bucket)
-- CREATE TABLE kg.facts_p0 PARTITION OF kg.facts FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.facts ALTER COLUMN fact_id TYPE text;

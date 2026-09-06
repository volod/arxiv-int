-- arxiv-int postgres extensions for aliases
-- source: urn:arxiv-int:contract:aliases:1.0.0@1.0.0
ALTER TABLE kg.aliases ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.aliases USING (bucket)
-- CREATE TABLE kg.aliases_p0 PARTITION OF kg.aliases FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.aliases ALTER COLUMN alias_id TYPE text;

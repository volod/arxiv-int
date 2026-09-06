-- arxiv-int postgres extensions for catalogs
-- source: urn:arxiv-int:contract:catalogs:1.0.0@1.0.0
ALTER TABLE kg.catalog_entries ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.catalog_entries USING (bucket)
-- CREATE TABLE kg.catalog_entries_p0 PARTITION OF kg.catalog_entries FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.catalog_entries ALTER COLUMN catalog_entry_id TYPE text;

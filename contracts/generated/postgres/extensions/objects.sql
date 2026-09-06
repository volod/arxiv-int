-- arxiv-int postgres extensions for objects
-- source: urn:arxiv-int:contract:objects:1.0.0@1.0.0
ALTER TABLE kg.objects ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.objects USING (bucket)
-- CREATE TABLE kg.objects_p0 PARTITION OF kg.objects FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.objects ALTER COLUMN object_id TYPE text;

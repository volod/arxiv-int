-- arxiv-int postgres extensions for mentions
-- source: urn:arxiv-int:contract:mentions:1.0.0@1.0.0
ALTER TABLE kg.mentions ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.mentions USING (bucket)
-- CREATE TABLE kg.mentions_p0 PARTITION OF kg.mentions FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.mentions ALTER COLUMN mention_id TYPE text;

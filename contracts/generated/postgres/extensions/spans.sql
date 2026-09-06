-- arxiv-int postgres extensions for spans
-- source: urn:arxiv-int:contract:spans:1.0.0@1.0.0
ALTER TABLE corpus.spans ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for corpus.spans USING (bucket)
-- CREATE TABLE corpus.spans_p0 PARTITION OF corpus.spans FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE corpus.spans ALTER COLUMN span_id TYPE text;

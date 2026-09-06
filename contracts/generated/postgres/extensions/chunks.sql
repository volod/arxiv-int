-- arxiv-int postgres extensions for chunks
-- source: urn:arxiv-int:contract:chunks:1.0.0@1.0.0
ALTER TABLE corpus.chunks ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for corpus.chunks USING (bucket)
-- CREATE TABLE corpus.chunks_p0 PARTITION OF corpus.chunks FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE corpus.chunks ALTER COLUMN chunk_id TYPE text;

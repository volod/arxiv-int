-- arxiv-int postgres extensions for embeddings
-- source: urn:arxiv-int:contract:embeddings:1.0.0@1.0.0
ALTER TABLE search.embeddings ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for search.embeddings USING (bucket)
-- CREATE TABLE search.embeddings_p0 PARTITION OF search.embeddings FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE search.embeddings ALTER COLUMN embedding_id TYPE text;

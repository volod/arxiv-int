-- arxiv-int vector extensions for embeddings
CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE search.embeddings ADD COLUMN IF NOT EXISTS embedding vector(1024);
CREATE INDEX IF NOT EXISTS embeddings_embedding_ivfflat ON search.embeddings USING ivfflat (embedding vector_cosine_ops);

-- Data Contract: urn:arxiv-int:contract:embeddings:1.0.0
-- Physical binding: search.embeddings
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS search;
CREATE TABLE search.embeddings (
	embedding_id TEXT NOT NULL,
	target_kind TEXT,
	target_id TEXT,
	profile_id TEXT,
	dimensions BIGINT,
	vector_ref TEXT,
	model_digest TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_embeddings PRIMARY KEY (embedding_id)
);
COMMENT ON TABLE search.embeddings IS 'Vector embedding references for retrieval targets under a profile.';
COMMENT ON COLUMN search.embeddings.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

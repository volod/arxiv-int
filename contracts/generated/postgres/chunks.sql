-- Data Contract: urn:arxiv-int:contract:chunks:1.0.0
-- Physical binding: corpus.chunks
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.chunks (
	chunk_id TEXT NOT NULL,
	document_id TEXT,
	chunker_id TEXT,
	ordinal BIGINT,
	text TEXT,
	start_char BIGINT,
	end_char BIGINT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_chunks PRIMARY KEY (chunk_id),
	CONSTRAINT fk_chunks_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE corpus.chunks IS 'Chunker-partitioned text units derived from documents for retrieval and extraction.';
COMMENT ON COLUMN corpus.chunks.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

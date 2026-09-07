-- Data Contract: urn:arxiv-int:contract:documents:1.0.0
-- Physical binding: corpus.documents
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.documents (
	document_id TEXT NOT NULL,
	content_hash TEXT,
	extractor_profile TEXT,
	media_type TEXT,
	language TEXT,
	title TEXT,
	byte_size BIGINT,
	text_chars BIGINT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_documents PRIMARY KEY (document_id)
);
COMMENT ON TABLE corpus.documents IS 'Normalized document identity and extracted text metadata for the archive corpus.';
COMMENT ON COLUMN corpus.documents.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

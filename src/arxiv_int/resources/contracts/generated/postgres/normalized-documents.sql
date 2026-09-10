-- Data Contract: urn:arxiv-int:contract:normalized-documents:1.0.0
-- Physical binding: corpus.normalized_documents
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.normalized_documents (
	normalized_document_id TEXT NOT NULL,
	document_id TEXT,
	normalizer_id TEXT,
	language TEXT,
	language_confidence DOUBLE PRECISION,
	normalized_sha256 TEXT,
	text_chars BIGINT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_normalized_documents PRIMARY KEY (normalized_document_id),
	CONSTRAINT fk_normalized_documents_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE corpus.normalized_documents IS 'Canonical normalized text views, detected language, and reversible offset maps.';
COMMENT ON COLUMN corpus.normalized_documents.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

-- Data Contract: urn:arxiv-int:contract:spans:1.0.0
-- Physical binding: corpus.spans
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.spans (
	span_id TEXT NOT NULL,
	document_id TEXT,
	start_char BIGINT,
	end_char BIGINT,
	page BIGINT,
	kind TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_spans PRIMARY KEY (span_id),
	CONSTRAINT fk_spans_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE corpus.spans IS 'Character-anchored spans locating evidence within documents.';
COMMENT ON COLUMN corpus.spans.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

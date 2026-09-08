-- Data Contract: urn:arxiv-int:contract:document-path-events:1.0.0
-- Physical binding: corpus.document_path_event
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.document_path_event (
	event_id TEXT NOT NULL,
	document_id TEXT NOT NULL,
	occurrence_id TEXT,
	silo_id TEXT NOT NULL,
	kind TEXT NOT NULL,
	relative_path TEXT NOT NULL,
	previous_relative_path TEXT,
	content_hash TEXT NOT NULL,
	ledger_id TEXT,
	event_time TIMESTAMP WITH TIME ZONE NOT NULL,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_document_path_event PRIMARY KEY (event_id),
	CONSTRAINT fk_document_path_event_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id),
	CONSTRAINT fk_document_path_event_occurrence_id FOREIGN KEY(occurrence_id) REFERENCES corpus.source_occurrences (occurrence_id)
);
COMMENT ON TABLE corpus.document_path_event IS 'Portable path events that record initial, renamed, copied, and imported locations for canonical documents.';
COMMENT ON COLUMN corpus.document_path_event.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

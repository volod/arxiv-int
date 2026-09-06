-- Data Contract: urn:arxiv-int:contract:source-occurrences:1.0.0
-- Physical binding: corpus.source_occurrences
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.source_occurrences (
	occurrence_id TEXT NOT NULL,
	silo_id TEXT,
	relative_path TEXT,
	scan_id TEXT,
	content_hash TEXT,
	container_path TEXT,
	member_path TEXT,
	status TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_source_occurrences PRIMARY KEY (occurrence_id)
);
COMMENT ON TABLE corpus.source_occurrences IS 'Silo-relative source locations and scan status for archive bytes.';
COMMENT ON COLUMN corpus.source_occurrences.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

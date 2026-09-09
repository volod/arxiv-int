-- Data Contract: urn:arxiv-int:contract:topics:1.0.0
-- Physical binding: search.topic_assignments
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS search;
CREATE TABLE search.topic_assignments (
	topic_assignment_id TEXT NOT NULL,
	topic_id TEXT,
	label TEXT,
	scheme_id TEXT,
	document_id TEXT,
	score NUMERIC,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_topic_assignments PRIMARY KEY (topic_assignment_id),
	CONSTRAINT fk_topic_assignments_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE search.topic_assignments IS 'Topic assignments linking documents to labeled topics under a scheme.';
COMMENT ON COLUMN search.topic_assignments.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

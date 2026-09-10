-- Data Contract: urn:arxiv-int:contract:duplicate-groups:1.0.0
-- Physical binding: corpus.duplicate_groups
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.duplicate_groups (
	duplicate_membership_id TEXT NOT NULL,
	group_id TEXT,
	document_id TEXT,
	method TEXT,
	role TEXT,
	score DOUBLE PRECISION,
	suppressed BOOLEAN,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_duplicate_groups PRIMARY KEY (duplicate_membership_id),
	CONSTRAINT fk_duplicate_groups_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE corpus.duplicate_groups IS 'Reversible duplicate and edition group memberships proposed over normalized documents.';
COMMENT ON COLUMN corpus.duplicate_groups.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

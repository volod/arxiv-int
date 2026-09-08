-- Data Contract: urn:arxiv-int:contract:objects:1.0.0
-- Physical binding: kg.objects
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.objects (
	object_id TEXT NOT NULL,
	object_type TEXT,
	preferred_label TEXT,
	lifecycle_state TEXT,
	review_state TEXT,
	cluster_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_objects PRIMARY KEY (object_id)
);
COMMENT ON TABLE kg.objects IS 'Canonical knowledge-graph objects with lifecycle and review state.';
COMMENT ON COLUMN kg.objects.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

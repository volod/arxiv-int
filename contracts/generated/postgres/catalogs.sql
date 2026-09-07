-- Data Contract: urn:arxiv-int:contract:catalogs:1.0.0
-- Physical binding: kg.catalog_entries
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.catalog_entries (
	catalog_entry_id TEXT NOT NULL,
	catalog_kind TEXT,
	object_id TEXT,
	preferred_name TEXT,
	document_count BIGINT,
	review_state TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_catalog_entries PRIMARY KEY (catalog_entry_id),
	CONSTRAINT fk_catalog_entries_object_id FOREIGN KEY(object_id) REFERENCES kg.objects (object_id)
);
COMMENT ON TABLE kg.catalog_entries IS 'Catalog entries summarizing objects with preferred names and document counts.';
COMMENT ON COLUMN kg.catalog_entries.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

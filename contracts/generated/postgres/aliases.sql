-- Data Contract: urn:arxiv-int:contract:aliases:1.0.0
-- Physical binding: kg.aliases
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.aliases (
	alias_id TEXT NOT NULL,
	object_id TEXT,
	alias_text TEXT,
	alias_kind TEXT,
	normalized_text TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_aliases PRIMARY KEY (alias_id),
	CONSTRAINT fk_aliases_object_id FOREIGN KEY(object_id) REFERENCES kg.objects (object_id)
);
COMMENT ON TABLE kg.aliases IS 'Alternate labels and normalized aliases for knowledge-graph objects.';
COMMENT ON COLUMN kg.aliases.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

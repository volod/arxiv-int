-- Data Contract: urn:arxiv-int:contract:domain-artifacts-bom:1.0.0
-- Physical binding: kg.bom_lines
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.bom_lines (
	bom_line_id TEXT NOT NULL,
	bom_id TEXT,
	root_object_id TEXT,
	parent_object_id TEXT,
	child_object_id TEXT,
	predicate_id TEXT,
	listing_kind TEXT,
	quantity NUMERIC,
	unit TEXT,
	alternative_group_id TEXT,
	is_mandatory BOOLEAN,
	effectivity_start TIMESTAMP WITH TIME ZONE,
	effectivity_end TIMESTAMP WITH TIME ZONE,
	revision_object_id TEXT,
	completeness_status TEXT,
	cycle_detected BOOLEAN,
	evidence_fact_ids TEXT,
	document_id TEXT,
	anchor_kind TEXT,
	review_state TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_bom_lines PRIMARY KEY (bom_line_id),
	CONSTRAINT fk_bom_lines_root_object_id FOREIGN KEY(root_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_bom_lines_parent_object_id FOREIGN KEY(parent_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_bom_lines_child_object_id FOREIGN KEY(child_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_bom_lines_revision_object_id FOREIGN KEY(revision_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_bom_lines_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE kg.bom_lines IS 'Bill-of-materials hierarchy rows with quantities, alternatives, effectivity, and completeness.';
COMMENT ON COLUMN kg.bom_lines.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

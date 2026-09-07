-- Data Contract: urn:arxiv-int:contract:domain-artifacts-relationship-map:1.0.0
-- Physical binding: kg.relationship_edges
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.relationship_edges (
	edge_id TEXT NOT NULL,
	subject_object_id TEXT,
	predicate_id TEXT,
	object_object_id TEXT,
	relation_kind TEXT,
	direction TEXT,
	cardinality TEXT,
	review_state TEXT,
	inclusion_policy TEXT,
	conflict_group_id TEXT,
	evidence_fact_ids TEXT,
	document_id TEXT,
	span_id TEXT,
	anchor_kind TEXT,
	confidence NUMERIC,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_relationship_edges PRIMARY KEY (edge_id),
	CONSTRAINT fk_relationship_edges_subject_object_id FOREIGN KEY(subject_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_relationship_edges_object_object_id FOREIGN KEY(object_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_relationship_edges_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id),
	CONSTRAINT fk_relationship_edges_span_id FOREIGN KEY(span_id) REFERENCES corpus.spans (span_id)
);
COMMENT ON TABLE kg.relationship_edges IS 'Typed design/party/product relationship edges with evidence and inclusion state.';
COMMENT ON COLUMN kg.relationship_edges.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

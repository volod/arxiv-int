-- Data Contract: urn:arxiv-int:contract:facts:1.0.0
-- Physical binding: kg.facts
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.facts (
	fact_id TEXT NOT NULL,
	subject_object_id TEXT,
	predicate_id TEXT,
	object_object_id TEXT,
	literal_value TEXT,
	literal_type TEXT,
	status TEXT,
	confidence NUMERIC,
	document_id TEXT,
	span_id TEXT,
	chunk_id TEXT,
	identity_snapshot_id TEXT,
	extractor_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_facts PRIMARY KEY (fact_id),
	CONSTRAINT fk_facts_subject_object_id FOREIGN KEY(subject_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_facts_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id),
	CONSTRAINT fk_facts_span_id FOREIGN KEY(span_id) REFERENCES corpus.spans (span_id),
	CONSTRAINT fk_facts_chunk_id FOREIGN KEY(chunk_id) REFERENCES corpus.chunks (chunk_id)
);
COMMENT ON TABLE kg.facts IS 'Extracted subject-predicate-object facts with evidence anchors and confidence.';
COMMENT ON COLUMN kg.facts.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

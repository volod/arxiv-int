-- Data Contract: urn:arxiv-int:contract:mentions:1.0.0
-- Physical binding: kg.mentions
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.mentions (
	mention_id TEXT NOT NULL,
	document_id TEXT,
	span_id TEXT,
	chunk_id TEXT,
	surface_form TEXT,
	object_anchor_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_mentions PRIMARY KEY (mention_id),
	CONSTRAINT fk_mentions_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id),
	CONSTRAINT fk_mentions_span_id FOREIGN KEY(span_id) REFERENCES corpus.spans (span_id),
	CONSTRAINT fk_mentions_chunk_id FOREIGN KEY(chunk_id) REFERENCES corpus.chunks (chunk_id)
);
COMMENT ON TABLE kg.mentions IS 'Surface-form mentions linking documents, spans, and chunks to object anchors.';
COMMENT ON COLUMN kg.mentions.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

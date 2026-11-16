-- Data Contract: urn:arxiv-int:contract:file-classifications:1.0.0
-- Physical binding: corpus.file_classification
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.file_classification (
	classification_id TEXT NOT NULL,
	occurrence_id TEXT NOT NULL,
	document_id TEXT,
	silo_id TEXT NOT NULL,
	relative_path TEXT NOT NULL,
	primary_class_id TEXT NOT NULL,
	alternate_class_ids_json TEXT NOT NULL,
	ancestor_path TEXT NOT NULL,
	confidence DOUBLE PRECISION NOT NULL,
	calibration_profile TEXT NOT NULL,
	scores_json TEXT NOT NULL,
	evidence_json TEXT NOT NULL,
	failure_reason TEXT,
	extraction_fingerprint TEXT NOT NULL,
	normalizer_id TEXT NOT NULL,
	classifier_id TEXT NOT NULL,
	configuration_sha256 TEXT NOT NULL,
	scheme_id TEXT NOT NULL,
	review_state TEXT NOT NULL,
	run_id TEXT NOT NULL,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_file_classification PRIMARY KEY (classification_id),
	CONSTRAINT fk_file_classification_occurrence_id FOREIGN KEY(occurrence_id) REFERENCES corpus.source_occurrences (occurrence_id),
	CONSTRAINT fk_file_classification_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE corpus.file_classification IS 'Complete, evidence-backed subject classification of physical archive files, including explicit unclassified and unreadable outcomes and the fingerprints needed to reproduce each decision.';
COMMENT ON COLUMN corpus.file_classification.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

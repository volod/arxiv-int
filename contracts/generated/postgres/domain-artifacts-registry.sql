-- Data Contract: urn:arxiv-int:contract:domain-artifacts-registry:1.0.0
-- Physical binding: ctl.domain_artifact_registry
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS ctl;
CREATE TABLE ctl.domain_artifact_registry (
	artifact_id TEXT NOT NULL,
	artifact_type TEXT,
	schema_version TEXT,
	generator_fingerprint TEXT,
	policy_fingerprint TEXT,
	input_fact_snapshot_id TEXT,
	identity_snapshot_id TEXT,
	review_inclusion_rules TEXT,
	uri_or_path TEXT,
	media_type TEXT,
	byte_count BIGINT,
	row_count BIGINT,
	checksum TEXT,
	evidence_coverage NUMERIC,
	creation_status TEXT,
	failure_reason TEXT,
	run_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	CONSTRAINT pk_domain_artifact_registry PRIMARY KEY (artifact_id)
);
COMMENT ON TABLE ctl.domain_artifact_registry IS 'Run artifact registry for domain investigation family outputs and creation statuses.';

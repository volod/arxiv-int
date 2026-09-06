-- Data Contract: urn:arxiv-int:contract:domain-artifacts-registry:1.0.0
-- SQL Dialect: postgres
CREATE TABLE domain_artifact_registry (
  artifact_id text not null primary key,
  artifact_type text,
  schema_version text,
  generator_fingerprint text,
  policy_fingerprint text,
  input_fact_snapshot_id text,
  identity_snapshot_id text,
  review_inclusion_rules text,
  uri_or_path text,
  media_type text,
  byte_count integer,
  row_count integer,
  checksum text,
  evidence_coverage numeric,
  creation_status text,
  failure_reason text,
  run_id text,
  generation_id text not null,
  contract_version text not null
);

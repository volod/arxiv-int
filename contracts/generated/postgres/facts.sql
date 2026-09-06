-- Data Contract: urn:arxiv-int:contract:facts:1.0.0
-- SQL Dialect: postgres
CREATE TABLE facts (
  fact_id text not null primary key,
  subject_object_id text,
  predicate_id text,
  object_object_id text,
  literal_value text,
  literal_type text,
  status text,
  confidence numeric,
  document_id text,
  span_id text,
  chunk_id text,
  identity_snapshot_id text,
  extractor_id text,
  generation_id text not null,
  contract_version text not null
);

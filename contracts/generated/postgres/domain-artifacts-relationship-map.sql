-- Data Contract: urn:arxiv-int:contract:domain-artifacts-relationship-map:1.0.0
-- SQL Dialect: postgres
CREATE TABLE relationship_edges (
  edge_id text not null primary key,
  subject_object_id text,
  predicate_id text,
  object_object_id text,
  relation_kind text,
  direction text,
  cardinality text,
  review_state text,
  inclusion_policy text,
  conflict_group_id text,
  evidence_fact_ids text,
  document_id text,
  span_id text,
  anchor_kind text,
  confidence numeric,
  generation_id text not null,
  contract_version text not null
);

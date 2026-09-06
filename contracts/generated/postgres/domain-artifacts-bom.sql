-- Data Contract: urn:arxiv-int:contract:domain-artifacts-bom:1.0.0
-- SQL Dialect: postgres
CREATE TABLE bom_lines (
  bom_line_id text not null primary key,
  bom_id text,
  root_object_id text,
  parent_object_id text,
  child_object_id text,
  predicate_id text,
  listing_kind text,
  quantity numeric,
  unit text,
  alternative_group_id text,
  is_mandatory boolean,
  effectivity_start timestamptz,
  effectivity_end timestamptz,
  revision_object_id text,
  completeness_status text,
  cycle_detected boolean,
  evidence_fact_ids text,
  document_id text,
  anchor_kind text,
  review_state text,
  generation_id text not null,
  contract_version text not null
);

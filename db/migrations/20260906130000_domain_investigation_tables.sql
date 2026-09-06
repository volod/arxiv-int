-- Domain investigation artifact tables generated from contracts/generated/postgres
-- Additive migration; no destructive SQL.

-- source: contracts/generated/postgres/domain-artifacts-relationship-map.sql
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

-- source: contracts/generated/postgres/domain-artifacts-bom.sql
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

-- source: contracts/generated/postgres/domain-artifacts-supply-chain.sql
-- Data Contract: urn:arxiv-int:contract:domain-artifacts-supply-chain:1.0.0
-- SQL Dialect: postgres
CREATE TABLE supply_chain_edges (
  edge_id text not null primary key,
  path_id text,
  stage text,
  from_object_id text,
  to_object_id text,
  role_predicate_id text,
  product_object_id text,
  transaction_id text,
  direction text,
  event_time timestamptz,
  status text,
  evidence_fact_ids text,
  document_id text,
  review_state text,
  confidence numeric,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/domain-artifacts-invoice-payment.sql
-- Data Contract: urn:arxiv-int:contract:domain-artifacts-invoice-payment:1.0.0
-- SQL Dialect: postgres
CREATE TABLE invoice_payment_rows (
  row_id text not null primary key,
  row_kind text,
  invoice_object_id text,
  payment_object_id text,
  line_number integer,
  amount numeric,
  allocated_amount numeric,
  currency text,
  due_date timestamptz,
  payment_date timestamptz,
  match_state text,
  allocation_group_id text,
  debit_credit text,
  evidence_fact_ids text,
  document_id text,
  review_state text,
  confidence numeric,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/domain-artifacts-registry.sql
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


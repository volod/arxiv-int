-- arxiv-int baseline relational schema generated from contracts/generated/postgres
-- Owned by dbmate-style migrations; do not auto-apply generated DDL to live stores.

-- source: contracts/generated/postgres/aliases.sql
CREATE TABLE aliases (
  alias_id text not null primary key,
  object_id text,
  alias_text text,
  alias_kind text,
  normalized_text text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/anomaly-findings.sql
CREATE TABLE anomaly_findings (
  finding_id text not null primary key,
  finding_type text,
  severity text,
  status text,
  subject_object_id text,
  rule_id text,
  evidence_summary text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/catalogs.sql
CREATE TABLE catalog_entries (
  catalog_entry_id text not null primary key,
  catalog_kind text,
  object_id text,
  preferred_name text,
  document_count integer,
  review_state text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/chunks.sql
CREATE TABLE chunks (
  chunk_id text not null primary key,
  document_id text,
  chunker_id text,
  ordinal integer,
  text text,
  start_char integer,
  end_char integer,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/documents.sql
CREATE TABLE documents (
  document_id text not null primary key,
  content_hash text,
  extractor_profile text,
  media_type text,
  language text,
  title text,
  byte_size integer,
  text_chars integer,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/embeddings.sql
CREATE TABLE embeddings (
  embedding_id text not null primary key,
  target_kind text,
  target_id text,
  profile_id text,
  dimensions integer,
  vector_ref text,
  model_digest text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/evaluation-items.sql
CREATE TABLE evaluation_items (
  evaluation_item_id text not null primary key,
  item_kind text,
  gold_ref text,
  split text,
  query_text text,
  label text,
  dataset_id text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/facts.sql
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

-- source: contracts/generated/postgres/mentions.sql
CREATE TABLE mentions (
  mention_id text not null primary key,
  document_id text,
  span_id text,
  chunk_id text,
  surface_form text,
  object_anchor_id text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/objects.sql
CREATE TABLE objects (
  object_id text not null primary key,
  object_type text,
  preferred_label text,
  lifecycle_state text,
  review_state text,
  cluster_id text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/ontology-terms.sql
CREATE TABLE terms (
  term_id text not null primary key,
  uri text,
  label text,
  kind text,
  domain_uri text,
  range_uri text,
  ontology_version text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/source-occurrences.sql
CREATE TABLE source_occurrences (
  occurrence_id text not null primary key,
  silo_id text,
  relative_path text,
  scan_id text,
  content_hash text,
  container_path text,
  member_path text,
  status text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/spans.sql
CREATE TABLE spans (
  span_id text not null primary key,
  document_id text,
  start_char integer,
  end_char integer,
  page integer,
  kind text,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/topics.sql
CREATE TABLE topic_assignments (
  topic_assignment_id text not null primary key,
  topic_id text,
  label text,
  scheme_id text,
  document_id text,
  score numeric,
  generation_id text not null,
  contract_version text not null
);

-- source: contracts/generated/postgres/transactions.sql
CREATE TABLE transactions (
  transaction_id text not null primary key,
  transaction_type text,
  amount numeric,
  currency text,
  party_subject_id text,
  party_object_id text,
  document_id text,
  event_time timestamptz,
  generation_id text not null,
  contract_version text not null
);

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

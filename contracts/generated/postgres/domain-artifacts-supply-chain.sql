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

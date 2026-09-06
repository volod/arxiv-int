-- Data Contract: urn:arxiv-int:contract:evaluation-items:1.0.0
-- SQL Dialect: postgres
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

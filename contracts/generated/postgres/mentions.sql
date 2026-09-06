-- Data Contract: urn:arxiv-int:contract:mentions:1.0.0
-- SQL Dialect: postgres
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

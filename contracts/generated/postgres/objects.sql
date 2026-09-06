-- Data Contract: urn:arxiv-int:contract:objects:1.0.0
-- SQL Dialect: postgres
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

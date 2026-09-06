-- Data Contract: urn:arxiv-int:contract:embeddings:1.0.0
-- SQL Dialect: postgres
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

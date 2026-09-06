-- Data Contract: urn:arxiv-int:contract:chunks:1.0.0
-- SQL Dialect: postgres
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

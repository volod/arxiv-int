-- Data Contract: urn:arxiv-int:contract:spans:1.0.0
-- SQL Dialect: postgres
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

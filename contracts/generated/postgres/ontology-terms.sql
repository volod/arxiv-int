-- Data Contract: urn:arxiv-int:contract:ontology-terms:1.0.0
-- SQL Dialect: postgres
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

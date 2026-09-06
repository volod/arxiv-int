-- Data Contract: urn:arxiv-int:contract:topics:1.0.0
-- SQL Dialect: postgres
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

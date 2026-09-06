-- Data Contract: urn:arxiv-int:contract:source-occurrences:1.0.0
-- SQL Dialect: postgres
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

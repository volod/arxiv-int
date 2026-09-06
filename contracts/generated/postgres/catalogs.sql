-- Data Contract: urn:arxiv-int:contract:catalogs:1.0.0
-- SQL Dialect: postgres
CREATE TABLE catalog_entries (
  catalog_entry_id text not null primary key,
  catalog_kind text,
  object_id text,
  preferred_name text,
  document_count integer,
  review_state text,
  generation_id text not null,
  contract_version text not null
);

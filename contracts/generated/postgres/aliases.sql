-- Data Contract: urn:arxiv-int:contract:aliases:1.0.0
-- SQL Dialect: postgres
CREATE TABLE aliases (
  alias_id text not null primary key,
  object_id text,
  alias_text text,
  alias_kind text,
  normalized_text text,
  generation_id text not null,
  contract_version text not null
);

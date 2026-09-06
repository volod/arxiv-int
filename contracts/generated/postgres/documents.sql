-- Data Contract: urn:arxiv-int:contract:documents:1.0.0
-- SQL Dialect: postgres
CREATE TABLE documents (
  document_id text not null primary key,
  content_hash text,
  extractor_profile text,
  media_type text,
  language text,
  title text,
  byte_size integer,
  text_chars integer,
  generation_id text not null,
  contract_version text not null
);

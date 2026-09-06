-- Data Contract: urn:arxiv-int:contract:transactions:1.0.0
-- SQL Dialect: postgres
CREATE TABLE transactions (
  transaction_id text not null primary key,
  transaction_type text,
  amount numeric,
  currency text,
  party_subject_id text,
  party_object_id text,
  document_id text,
  event_time timestamptz,
  generation_id text not null,
  contract_version text not null
);

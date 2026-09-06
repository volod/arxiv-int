-- Data Contract: urn:arxiv-int:contract:domain-artifacts-invoice-payment:1.0.0
-- SQL Dialect: postgres
CREATE TABLE invoice_payment_rows (
  row_id text not null primary key,
  row_kind text,
  invoice_object_id text,
  payment_object_id text,
  line_number integer,
  amount numeric,
  allocated_amount numeric,
  currency text,
  due_date timestamptz,
  payment_date timestamptz,
  match_state text,
  allocation_group_id text,
  debit_credit text,
  evidence_fact_ids text,
  document_id text,
  review_state text,
  confidence numeric,
  generation_id text not null,
  contract_version text not null
);

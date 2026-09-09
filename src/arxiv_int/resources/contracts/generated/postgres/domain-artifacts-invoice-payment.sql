-- Data Contract: urn:arxiv-int:contract:domain-artifacts-invoice-payment:1.0.0
-- Physical binding: kg.invoice_payment_rows
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.invoice_payment_rows (
	row_id TEXT NOT NULL,
	row_kind TEXT,
	invoice_object_id TEXT,
	payment_object_id TEXT,
	line_number BIGINT,
	amount NUMERIC,
	allocated_amount NUMERIC,
	currency TEXT,
	due_date TIMESTAMP WITH TIME ZONE,
	payment_date TIMESTAMP WITH TIME ZONE,
	match_state TEXT,
	allocation_group_id TEXT,
	debit_credit TEXT,
	evidence_fact_ids TEXT,
	document_id TEXT,
	review_state TEXT,
	confidence NUMERIC,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_invoice_payment_rows PRIMARY KEY (row_id),
	CONSTRAINT fk_invoice_payment_rows_invoice_object_id FOREIGN KEY(invoice_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_invoice_payment_rows_payment_object_id FOREIGN KEY(payment_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_invoice_payment_rows_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE kg.invoice_payment_rows IS 'Invoice lines, payments, credit notes, ledger postings, and allocation match states.';
COMMENT ON COLUMN kg.invoice_payment_rows.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

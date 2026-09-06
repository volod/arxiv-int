-- Data Contract: urn:arxiv-int:contract:transactions:1.0.0
-- Physical binding: kg.transactions
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.transactions (
	transaction_id TEXT NOT NULL,
	transaction_type TEXT,
	amount NUMERIC,
	currency TEXT,
	party_subject_id TEXT,
	party_object_id TEXT,
	document_id TEXT,
	event_time TIMESTAMP WITH TIME ZONE,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_transactions PRIMARY KEY (transaction_id),
	CONSTRAINT fk_transactions_party_subject_id FOREIGN KEY(party_subject_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_transactions_party_object_id FOREIGN KEY(party_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_transactions_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE kg.transactions IS 'Financial or exchange transactions linked to parties and source documents.';
COMMENT ON COLUMN kg.transactions.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

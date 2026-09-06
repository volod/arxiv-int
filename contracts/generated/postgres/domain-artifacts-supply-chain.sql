-- Data Contract: urn:arxiv-int:contract:domain-artifacts-supply-chain:1.0.0
-- Physical binding: kg.supply_chain_edges
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS kg;
CREATE TABLE kg.supply_chain_edges (
	edge_id TEXT NOT NULL,
	path_id TEXT,
	stage TEXT,
	from_object_id TEXT,
	to_object_id TEXT,
	role_predicate_id TEXT,
	product_object_id TEXT,
	transaction_id TEXT,
	direction TEXT,
	event_time TIMESTAMP WITH TIME ZONE,
	status TEXT,
	evidence_fact_ids TEXT,
	document_id TEXT,
	review_state TEXT,
	confidence NUMERIC,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_supply_chain_edges PRIMARY KEY (edge_id),
	CONSTRAINT fk_supply_chain_edges_from_object_id FOREIGN KEY(from_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_supply_chain_edges_to_object_id FOREIGN KEY(to_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_supply_chain_edges_product_object_id FOREIGN KEY(product_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_supply_chain_edges_transaction_id FOREIGN KEY(transaction_id) REFERENCES kg.transactions (transaction_id),
	CONSTRAINT fk_supply_chain_edges_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE kg.supply_chain_edges IS 'Supply-chain stage edges separating quote, order, invoice, ship, receive, and pay claims.';
COMMENT ON COLUMN kg.supply_chain_edges.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

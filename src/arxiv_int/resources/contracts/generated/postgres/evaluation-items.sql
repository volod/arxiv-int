-- Data Contract: urn:arxiv-int:contract:evaluation-items:1.0.0
-- Physical binding: eval.evaluation_items
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS eval;
CREATE TABLE eval.evaluation_items (
	evaluation_item_id TEXT NOT NULL,
	item_kind TEXT,
	gold_ref TEXT,
	split TEXT,
	query_text TEXT,
	label TEXT,
	dataset_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	CONSTRAINT pk_evaluation_items PRIMARY KEY (evaluation_item_id)
);
COMMENT ON TABLE eval.evaluation_items IS 'Frozen evaluation items with gold references, splits, and labels.';

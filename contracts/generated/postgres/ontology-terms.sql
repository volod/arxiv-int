-- Data Contract: urn:arxiv-int:contract:ontology-terms:1.0.0
-- Physical binding: ontology.terms
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS ontology;
CREATE TABLE ontology.terms (
	term_id TEXT NOT NULL,
	uri TEXT,
	label TEXT,
	kind TEXT,
	domain_uri TEXT,
	range_uri TEXT,
	ontology_version TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	CONSTRAINT pk_terms PRIMARY KEY (term_id)
);
COMMENT ON TABLE ontology.terms IS 'Controlled ontology terms with URIs, labels, and domain or range constraints.';

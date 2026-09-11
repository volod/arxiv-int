-- Data Contract: urn:arxiv-int:contract:classification-classes:1.0.0
-- Physical binding: corpus.classification_classes
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE TABLE corpus.classification_classes (
	scheme_class_id TEXT NOT NULL,
	scheme_id TEXT NOT NULL,
	class_id TEXT NOT NULL,
	namespace TEXT NOT NULL,
	code TEXT,
	parent_class_id TEXT,
	ancestor_path TEXT NOT NULL,
	depth BIGINT NOT NULL,
	class_kind TEXT NOT NULL,
	caption_en TEXT,
	caption_ru TEXT,
	caption_uk TEXT,
	captions_json TEXT NOT NULL,
	crosswalk_json TEXT NOT NULL,
	path_token TEXT NOT NULL,
	slug TEXT,
	scheme_version TEXT NOT NULL,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	CONSTRAINT pk_classification_classes PRIMARY KEY (scheme_class_id)
);
COMMENT ON TABLE corpus.classification_classes IS 'Frozen classes of one versioned subject-taxonomy classification scheme: taxonomy classes, operator extensions and the unclassified/unreadable outcomes, with parent closure, multilingual captions, source crosswalk, and reversible path tokens.';

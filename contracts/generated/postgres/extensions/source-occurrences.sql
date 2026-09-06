-- arxiv-int postgres extensions for source-occurrences
-- source: urn:arxiv-int:contract:source-occurrences:1.0.0@1.0.0
ALTER TABLE corpus.source_occurrences ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for corpus.source_occurrences USING (bucket)
-- CREATE TABLE corpus.source_occurrences_p0 PARTITION OF corpus.source_occurrences FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE corpus.source_occurrences ALTER COLUMN occurrence_id TYPE text;

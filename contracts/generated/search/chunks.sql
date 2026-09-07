-- arxiv-int search extensions for chunks
-- tokenizer: russian_stem
CREATE INDEX IF NOT EXISTS chunks_text_bm25 ON corpus.chunks USING bm25 (text) WITH (key_field='text', text_config='russian_stem');

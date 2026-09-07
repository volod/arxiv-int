-- arxiv-int search extensions for documents
-- tokenizer: russian_stem
CREATE INDEX IF NOT EXISTS documents_title_bm25 ON corpus.documents USING bm25 (title) WITH (key_field='title', text_config='russian_stem');

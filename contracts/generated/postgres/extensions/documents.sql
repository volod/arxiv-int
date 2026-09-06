-- arxiv-int postgres extensions for documents
-- source: urn:arxiv-int:contract:documents:1.0.0@1.0.0
ALTER TABLE corpus.documents ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for corpus.documents USING (bucket)
-- CREATE TABLE corpus.documents_p0 PARTITION OF corpus.documents FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE corpus.documents ALTER COLUMN document_id TYPE text;

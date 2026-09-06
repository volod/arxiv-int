-- arxiv-int postgres extensions for domain-artifacts-bom
-- source: urn:arxiv-int:contract:domain-artifacts-bom:1.0.0@1.0.0
ALTER TABLE kg.bom_lines ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.bom_lines USING (bucket)
-- CREATE TABLE kg.bom_lines_p0 PARTITION OF kg.bom_lines FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.bom_lines ALTER COLUMN bom_line_id TYPE text;

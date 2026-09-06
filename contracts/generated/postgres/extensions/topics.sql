-- arxiv-int postgres extensions for topics
-- source: urn:arxiv-int:contract:topics:1.0.0@1.0.0
ALTER TABLE search.topic_assignments ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for search.topic_assignments USING (bucket)
-- CREATE TABLE search.topic_assignments_p0 PARTITION OF search.topic_assignments FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE search.topic_assignments ALTER COLUMN topic_assignment_id TYPE text;

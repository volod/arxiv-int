-- arxiv-int postgres extensions for transactions
-- source: urn:arxiv-int:contract:transactions:1.0.0@1.0.0
ALTER TABLE kg.transactions ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.transactions USING (bucket)
-- CREATE TABLE kg.transactions_p0 PARTITION OF kg.transactions FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.transactions ALTER COLUMN transaction_id TYPE text;

-- arxiv-int postgres extensions for domain-artifacts-invoice-payment
-- source: urn:arxiv-int:contract:domain-artifacts-invoice-payment:1.0.0@1.0.0
ALTER TABLE kg.invoice_payment_rows ADD COLUMN IF NOT EXISTS bucket text;
-- HASH partition template for kg.invoice_payment_rows USING (bucket)
-- CREATE TABLE kg.invoice_payment_rows_p0 PARTITION OF kg.invoice_payment_rows FOR VALUES WITH (MODULUS 16, REMAINDER 0);
ALTER TABLE kg.invoice_payment_rows ALTER COLUMN row_id TYPE text;

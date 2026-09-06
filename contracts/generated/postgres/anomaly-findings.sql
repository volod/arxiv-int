-- Data Contract: urn:arxiv-int:contract:anomaly-findings:1.0.0
-- SQL Dialect: postgres
CREATE TABLE anomaly_findings (
  finding_id text not null primary key,
  finding_type text,
  severity text,
  status text,
  subject_object_id text,
  rule_id text,
  evidence_summary text,
  generation_id text not null,
  contract_version text not null
);

-- Data Contract: urn:arxiv-int:contract:anomaly-findings:1.0.0
-- Physical binding: eval.anomaly_findings
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS eval;
CREATE TABLE eval.anomaly_findings (
	finding_id TEXT NOT NULL,
	finding_type TEXT,
	severity TEXT,
	status TEXT,
	subject_object_id TEXT,
	rule_id TEXT,
	evidence_summary TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	CONSTRAINT pk_anomaly_findings PRIMARY KEY (finding_id),
	CONSTRAINT fk_anomaly_findings_subject_object_id FOREIGN KEY(subject_object_id) REFERENCES kg.objects (object_id)
);
COMMENT ON TABLE eval.anomaly_findings IS 'Anomaly findings with severity, status, and evidence summaries for review.';

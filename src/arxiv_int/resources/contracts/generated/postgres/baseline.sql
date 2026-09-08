-- arxiv-int canonical baseline DDL
-- Compiled from contract-derived SQLAlchemy metadata (PostgreSQL dialect)
CREATE SCHEMA IF NOT EXISTS corpus;
CREATE SCHEMA IF NOT EXISTS ctl;
CREATE SCHEMA IF NOT EXISTS eval;
CREATE SCHEMA IF NOT EXISTS kg;
CREATE SCHEMA IF NOT EXISTS ontology;
CREATE SCHEMA IF NOT EXISTS search;
CREATE TABLE corpus.documents (
	document_id TEXT NOT NULL,
	content_hash TEXT,
	extractor_profile TEXT,
	media_type TEXT,
	language TEXT,
	title TEXT,
	byte_size BIGINT,
	text_chars BIGINT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_documents PRIMARY KEY (document_id)
);
COMMENT ON TABLE corpus.documents IS 'Normalized document identity and extracted text metadata for the archive corpus.';
COMMENT ON COLUMN corpus.documents.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE corpus.source_occurrences (
	occurrence_id TEXT NOT NULL,
	silo_id TEXT,
	relative_path TEXT,
	scan_id TEXT,
	content_hash TEXT,
	container_path TEXT,
	member_path TEXT,
	status TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_source_occurrences PRIMARY KEY (occurrence_id)
);
COMMENT ON TABLE corpus.source_occurrences IS 'Silo-relative source locations and scan status for archive bytes.';
COMMENT ON COLUMN corpus.source_occurrences.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE ctl.domain_artifact_registry (
	artifact_id TEXT NOT NULL,
	artifact_type TEXT,
	schema_version TEXT,
	generator_fingerprint TEXT,
	policy_fingerprint TEXT,
	input_fact_snapshot_id TEXT,
	identity_snapshot_id TEXT,
	review_inclusion_rules TEXT,
	uri_or_path TEXT,
	media_type TEXT,
	byte_count BIGINT,
	row_count BIGINT,
	checksum TEXT,
	evidence_coverage NUMERIC,
	creation_status TEXT,
	failure_reason TEXT,
	run_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	CONSTRAINT pk_domain_artifact_registry PRIMARY KEY (artifact_id)
);
COMMENT ON TABLE ctl.domain_artifact_registry IS 'Run artifact registry for domain investigation family outputs and creation statuses.';
CREATE TABLE eval.evaluation_items (
	evaluation_item_id TEXT NOT NULL,
	item_kind TEXT,
	gold_ref TEXT,
	split TEXT,
	query_text TEXT,
	label TEXT,
	dataset_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	CONSTRAINT pk_evaluation_items PRIMARY KEY (evaluation_item_id)
);
COMMENT ON TABLE eval.evaluation_items IS 'Frozen evaluation items with gold references, splits, and labels.';
CREATE TABLE kg.objects (
	object_id TEXT NOT NULL,
	object_type TEXT,
	preferred_label TEXT,
	lifecycle_state TEXT,
	review_state TEXT,
	cluster_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_objects PRIMARY KEY (object_id)
);
COMMENT ON TABLE kg.objects IS 'Canonical knowledge-graph objects with lifecycle and review state.';
COMMENT ON COLUMN kg.objects.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE ontology.terms (
	term_id TEXT NOT NULL,
	uri TEXT,
	label TEXT,
	kind TEXT,
	domain_uri TEXT,
	range_uri TEXT,
	ontology_version TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	CONSTRAINT pk_terms PRIMARY KEY (term_id)
);
COMMENT ON TABLE ontology.terms IS 'Controlled ontology terms with URIs, labels, and domain or range constraints.';
CREATE TABLE search.embeddings (
	embedding_id TEXT NOT NULL,
	target_kind TEXT,
	target_id TEXT,
	profile_id TEXT,
	dimensions BIGINT,
	vector_ref TEXT,
	model_digest TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_embeddings PRIMARY KEY (embedding_id)
);
COMMENT ON TABLE search.embeddings IS 'Vector embedding references for retrieval targets under a profile.';
COMMENT ON COLUMN search.embeddings.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE corpus.chunks (
	chunk_id TEXT NOT NULL,
	document_id TEXT,
	chunker_id TEXT,
	ordinal BIGINT,
	text TEXT,
	start_char BIGINT,
	end_char BIGINT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_chunks PRIMARY KEY (chunk_id),
	CONSTRAINT fk_chunks_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE corpus.chunks IS 'Chunker-partitioned text units derived from documents for retrieval and extraction.';
COMMENT ON COLUMN corpus.chunks.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE corpus.spans (
	span_id TEXT NOT NULL,
	document_id TEXT,
	start_char BIGINT,
	end_char BIGINT,
	page BIGINT,
	kind TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_spans PRIMARY KEY (span_id),
	CONSTRAINT fk_spans_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE corpus.spans IS 'Character-anchored spans locating evidence within documents.';
COMMENT ON COLUMN corpus.spans.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
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
CREATE TABLE kg.aliases (
	alias_id TEXT NOT NULL,
	object_id TEXT,
	alias_text TEXT,
	alias_kind TEXT,
	normalized_text TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_aliases PRIMARY KEY (alias_id),
	CONSTRAINT fk_aliases_object_id FOREIGN KEY(object_id) REFERENCES kg.objects (object_id)
);
COMMENT ON TABLE kg.aliases IS 'Alternate labels and normalized aliases for knowledge-graph objects.';
COMMENT ON COLUMN kg.aliases.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE kg.bom_lines (
	bom_line_id TEXT NOT NULL,
	bom_id TEXT,
	root_object_id TEXT,
	parent_object_id TEXT,
	child_object_id TEXT,
	predicate_id TEXT,
	listing_kind TEXT,
	quantity NUMERIC,
	unit TEXT,
	alternative_group_id TEXT,
	is_mandatory BOOLEAN,
	effectivity_start TIMESTAMP WITH TIME ZONE,
	effectivity_end TIMESTAMP WITH TIME ZONE,
	revision_object_id TEXT,
	completeness_status TEXT,
	cycle_detected BOOLEAN,
	evidence_fact_ids TEXT,
	document_id TEXT,
	anchor_kind TEXT,
	review_state TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_bom_lines PRIMARY KEY (bom_line_id),
	CONSTRAINT fk_bom_lines_root_object_id FOREIGN KEY(root_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_bom_lines_parent_object_id FOREIGN KEY(parent_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_bom_lines_child_object_id FOREIGN KEY(child_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_bom_lines_revision_object_id FOREIGN KEY(revision_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_bom_lines_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE kg.bom_lines IS 'Bill-of-materials hierarchy rows with quantities, alternatives, effectivity, and completeness.';
COMMENT ON COLUMN kg.bom_lines.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE kg.catalog_entries (
	catalog_entry_id TEXT NOT NULL,
	catalog_kind TEXT,
	object_id TEXT,
	preferred_name TEXT,
	document_count BIGINT,
	review_state TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_catalog_entries PRIMARY KEY (catalog_entry_id),
	CONSTRAINT fk_catalog_entries_object_id FOREIGN KEY(object_id) REFERENCES kg.objects (object_id)
);
COMMENT ON TABLE kg.catalog_entries IS 'Catalog entries summarizing objects with preferred names and document counts.';
COMMENT ON COLUMN kg.catalog_entries.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE kg.invoice_payment_rows (
	row_id TEXT NOT NULL,
	row_kind TEXT,
	invoice_object_id TEXT,
	payment_object_id TEXT,
	line_number BIGINT,
	amount NUMERIC,
	allocated_amount NUMERIC,
	currency TEXT,
	due_date TIMESTAMP WITH TIME ZONE,
	payment_date TIMESTAMP WITH TIME ZONE,
	match_state TEXT,
	allocation_group_id TEXT,
	debit_credit TEXT,
	evidence_fact_ids TEXT,
	document_id TEXT,
	review_state TEXT,
	confidence NUMERIC,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_invoice_payment_rows PRIMARY KEY (row_id),
	CONSTRAINT fk_invoice_payment_rows_invoice_object_id FOREIGN KEY(invoice_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_invoice_payment_rows_payment_object_id FOREIGN KEY(payment_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_invoice_payment_rows_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE kg.invoice_payment_rows IS 'Invoice lines, payments, credit notes, ledger postings, and allocation match states.';
COMMENT ON COLUMN kg.invoice_payment_rows.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE kg.transactions (
	transaction_id TEXT NOT NULL,
	transaction_type TEXT,
	amount NUMERIC,
	currency TEXT,
	party_subject_id TEXT,
	party_object_id TEXT,
	document_id TEXT,
	event_time TIMESTAMP WITH TIME ZONE,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_transactions PRIMARY KEY (transaction_id),
	CONSTRAINT fk_transactions_party_subject_id FOREIGN KEY(party_subject_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_transactions_party_object_id FOREIGN KEY(party_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_transactions_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE kg.transactions IS 'Financial or exchange transactions linked to parties and source documents.';
COMMENT ON COLUMN kg.transactions.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE search.topic_assignments (
	topic_assignment_id TEXT NOT NULL,
	topic_id TEXT,
	label TEXT,
	scheme_id TEXT,
	document_id TEXT,
	score NUMERIC,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_topic_assignments PRIMARY KEY (topic_assignment_id),
	CONSTRAINT fk_topic_assignments_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE search.topic_assignments IS 'Topic assignments linking documents to labeled topics under a scheme.';
COMMENT ON COLUMN search.topic_assignments.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE kg.facts (
	fact_id TEXT NOT NULL,
	subject_object_id TEXT,
	predicate_id TEXT,
	object_object_id TEXT,
	literal_value TEXT,
	literal_type TEXT,
	status TEXT,
	confidence NUMERIC,
	document_id TEXT,
	span_id TEXT,
	chunk_id TEXT,
	identity_snapshot_id TEXT,
	extractor_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_facts PRIMARY KEY (fact_id),
	CONSTRAINT fk_facts_subject_object_id FOREIGN KEY(subject_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_facts_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id),
	CONSTRAINT fk_facts_span_id FOREIGN KEY(span_id) REFERENCES corpus.spans (span_id),
	CONSTRAINT fk_facts_chunk_id FOREIGN KEY(chunk_id) REFERENCES corpus.chunks (chunk_id)
);
COMMENT ON TABLE kg.facts IS 'Extracted subject-predicate-object facts with evidence anchors and confidence.';
COMMENT ON COLUMN kg.facts.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE kg.mentions (
	mention_id TEXT NOT NULL,
	document_id TEXT,
	span_id TEXT,
	chunk_id TEXT,
	surface_form TEXT,
	object_anchor_id TEXT,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_mentions PRIMARY KEY (mention_id),
	CONSTRAINT fk_mentions_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id),
	CONSTRAINT fk_mentions_span_id FOREIGN KEY(span_id) REFERENCES corpus.spans (span_id),
	CONSTRAINT fk_mentions_chunk_id FOREIGN KEY(chunk_id) REFERENCES corpus.chunks (chunk_id)
);
COMMENT ON TABLE kg.mentions IS 'Surface-form mentions linking documents, spans, and chunks to object anchors.';
COMMENT ON COLUMN kg.mentions.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE kg.relationship_edges (
	edge_id TEXT NOT NULL,
	subject_object_id TEXT,
	predicate_id TEXT,
	object_object_id TEXT,
	relation_kind TEXT,
	direction TEXT,
	cardinality TEXT,
	review_state TEXT,
	inclusion_policy TEXT,
	conflict_group_id TEXT,
	evidence_fact_ids TEXT,
	document_id TEXT,
	span_id TEXT,
	anchor_kind TEXT,
	confidence NUMERIC,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_relationship_edges PRIMARY KEY (edge_id),
	CONSTRAINT fk_relationship_edges_subject_object_id FOREIGN KEY(subject_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_relationship_edges_object_object_id FOREIGN KEY(object_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_relationship_edges_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id),
	CONSTRAINT fk_relationship_edges_span_id FOREIGN KEY(span_id) REFERENCES corpus.spans (span_id)
);
COMMENT ON TABLE kg.relationship_edges IS 'Typed design/party/product relationship edges with evidence and inclusion state.';
COMMENT ON COLUMN kg.relationship_edges.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';
CREATE TABLE kg.supply_chain_edges (
	edge_id TEXT NOT NULL,
	path_id TEXT,
	stage TEXT,
	from_object_id TEXT,
	to_object_id TEXT,
	role_predicate_id TEXT,
	product_object_id TEXT,
	transaction_id TEXT,
	direction TEXT,
	event_time TIMESTAMP WITH TIME ZONE,
	status TEXT,
	evidence_fact_ids TEXT,
	document_id TEXT,
	review_state TEXT,
	confidence NUMERIC,
	generation_id TEXT NOT NULL,
	contract_version TEXT NOT NULL,
	bucket TEXT,
	CONSTRAINT pk_supply_chain_edges PRIMARY KEY (edge_id),
	CONSTRAINT fk_supply_chain_edges_from_object_id FOREIGN KEY(from_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_supply_chain_edges_to_object_id FOREIGN KEY(to_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_supply_chain_edges_product_object_id FOREIGN KEY(product_object_id) REFERENCES kg.objects (object_id),
	CONSTRAINT fk_supply_chain_edges_transaction_id FOREIGN KEY(transaction_id) REFERENCES kg.transactions (transaction_id),
	CONSTRAINT fk_supply_chain_edges_document_id FOREIGN KEY(document_id) REFERENCES corpus.documents (document_id)
);
COMMENT ON TABLE kg.supply_chain_edges IS 'Supply-chain stage edges separating quote, order, invoice, ship, receive, and pay claims.';
COMMENT ON COLUMN kg.supply_chain_edges.bucket IS 'Declared physical partition key from x-arxiv-int.partitionKey.';

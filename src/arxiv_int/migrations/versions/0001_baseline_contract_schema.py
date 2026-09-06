"""baseline contract schema

Generated from contract-derived SQLAlchemy metadata. Definitions below are frozen:
this revision never imports today's contracts to decide what it creates.

Revision ID: 0001
Revises: base
Contract fingerprints: see CONTRACT_FINGERPRINTS.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {
    "aliases": "urn:arxiv-int:contract:aliases:1.0.0@1.0.0:a561948012ae0f628c1e138304c902213acdd7d7c4d498d8df4b8e1859251d32",
    "anomaly-findings": "urn:arxiv-int:contract:anomaly-findings:1.0.0@1.0.0:4df06b330e215f4667aa60f05b5d216a75a8271f6560094df85574acc529c0ad",
    "catalogs": "urn:arxiv-int:contract:catalogs:1.0.0@1.0.0:b22834a1446f8709cb247f26262a511174c1e5dd95f1f40507762c133260e737",
    "chunks": "urn:arxiv-int:contract:chunks:1.0.0@1.0.0:307de21efa13da3e18d6dfc8393d9ea9d7c499023dfad346163dab3f32986cd9",
    "documents": "urn:arxiv-int:contract:documents:1.0.0@1.0.0:310be9094a64330b47ab31641053480fce0d90287febb43b185f9f63b9508bb9",
    "domain-artifacts-bom": "urn:arxiv-int:contract:domain-artifacts-bom:1.0.0@1.0.0:0e834538c0a06ef2d2982cbf51dcba914130681a19c34554b53524f65f51bc9f",
    "domain-artifacts-invoice-payment": "urn:arxiv-int:contract:domain-artifacts-invoice-payment:1.0.0@1.0.0:e804bf161026cc914ff628e80d1ad2d64b34222f347a7acac6103e68c28e5a1f",
    "domain-artifacts-registry": "urn:arxiv-int:contract:domain-artifacts-registry:1.0.0@1.0.0:61f501c3551539e3dd62a9165aa6c4824296163e07274313a4015abdf0c79ded",
    "domain-artifacts-relationship-map": "urn:arxiv-int:contract:domain-artifacts-relationship-map:1.0.0@1.0.0:0e69610485706859628856a1c1b197bbed52bb2c1cf61367e9b6930ac5ebed71",
    "domain-artifacts-supply-chain": "urn:arxiv-int:contract:domain-artifacts-supply-chain:1.0.0@1.0.0:33903f91359648be4f3a9cafb82f229bfa61c74430d00988d7c7b52119a54fbc",
    "embeddings": "urn:arxiv-int:contract:embeddings:1.0.0@1.0.0:aaab1f6568f261e4beec82c080adc97fd9fce7657079038da91ee4a89b599504",
    "evaluation-items": "urn:arxiv-int:contract:evaluation-items:1.0.0@1.0.0:4872b90c395c64cf24c72e4bba2c062dc4a3f48da1596b8096250931c6df70b0",
    "facts": "urn:arxiv-int:contract:facts:1.0.0@1.0.0:d53461b5a7070b3c34a3041e3fce345435aca25afc16866c53a8105159319969",
    "mentions": "urn:arxiv-int:contract:mentions:1.0.0@1.0.0:72bb044006f29893aa53a489944a56b21a090f9b7a85b46f3a41bf55bde4e94d",
    "objects": "urn:arxiv-int:contract:objects:1.0.0@1.0.0:aa5b00325935c7f69a3c656bdd632c933c0f7b26f65df199804b354f076df18a",
    "ontology-terms": "urn:arxiv-int:contract:ontology-terms:1.0.0@1.0.0:c9b2bf052d617fa9387f34dd1568bb46f6d89a46ce0205b73d65e35c45bc5e41",
    "source-occurrences": "urn:arxiv-int:contract:source-occurrences:1.0.0@1.0.0:2c6102d0cf82a82e0199ed780ac01ecafb561c4c7cf3f15789643945446ffd75",
    "spans": "urn:arxiv-int:contract:spans:1.0.0@1.0.0:499653b788b2a74e7afa78eb2cc3e082fd9cad7cd2a3fdd7c3bd23901902307b",
    "topics": "urn:arxiv-int:contract:topics:1.0.0@1.0.0:7f317a00986dae893ed207882df478882503d7fbde678d9cb7c76d6b681e5151",
    "transactions": "urn:arxiv-int:contract:transactions:1.0.0@1.0.0:304478e93fdd2d2145ffcb79b902ab56f7e360c7ac89aa53ea8de65074a5b870",
}
REVIEW_NOTES: tuple[str, ...] = ()
IRREVERSIBLE_REASON: str = ""


def upgrade() -> None:
    """Apply the frozen operations reviewed with this revision."""
    op.execute("CREATE SCHEMA IF NOT EXISTS corpus")
    op.execute("CREATE SCHEMA IF NOT EXISTS ctl")
    op.execute("CREATE SCHEMA IF NOT EXISTS eval")
    op.execute("CREATE SCHEMA IF NOT EXISTS kg")
    op.execute("CREATE SCHEMA IF NOT EXISTS ontology")
    op.execute("CREATE SCHEMA IF NOT EXISTS search")
    op.create_table(
        "documents",
        sa.Column("document_id", sa.Text(), nullable=False, comment=None),
        sa.Column("content_hash", sa.Text(), nullable=True, comment=None),
        sa.Column("extractor_profile", sa.Text(), nullable=True, comment=None),
        sa.Column("media_type", sa.Text(), nullable=True, comment=None),
        sa.Column("language", sa.Text(), nullable=True, comment=None),
        sa.Column("title", sa.Text(), nullable=True, comment=None),
        sa.Column("byte_size", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("text_chars", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("document_id", name="pk_documents"),
        schema="corpus",
        comment="Normalized document identity and extracted text metadata for the archive corpus.",
    )
    op.create_table(
        "source_occurrences",
        sa.Column("occurrence_id", sa.Text(), nullable=False, comment=None),
        sa.Column("silo_id", sa.Text(), nullable=True, comment=None),
        sa.Column("relative_path", sa.Text(), nullable=True, comment=None),
        sa.Column("scan_id", sa.Text(), nullable=True, comment=None),
        sa.Column("content_hash", sa.Text(), nullable=True, comment=None),
        sa.Column("container_path", sa.Text(), nullable=True, comment=None),
        sa.Column("member_path", sa.Text(), nullable=True, comment=None),
        sa.Column("status", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("occurrence_id", name="pk_source_occurrences"),
        schema="corpus",
        comment="Silo-relative source locations and scan status for archive bytes.",
    )
    op.create_table(
        "domain_artifact_registry",
        sa.Column("artifact_id", sa.Text(), nullable=False, comment=None),
        sa.Column("artifact_type", sa.Text(), nullable=True, comment=None),
        sa.Column("schema_version", sa.Text(), nullable=True, comment=None),
        sa.Column("generator_fingerprint", sa.Text(), nullable=True, comment=None),
        sa.Column("policy_fingerprint", sa.Text(), nullable=True, comment=None),
        sa.Column("input_fact_snapshot_id", sa.Text(), nullable=True, comment=None),
        sa.Column("identity_snapshot_id", sa.Text(), nullable=True, comment=None),
        sa.Column("review_inclusion_rules", sa.Text(), nullable=True, comment=None),
        sa.Column("uri_or_path", sa.Text(), nullable=True, comment=None),
        sa.Column("media_type", sa.Text(), nullable=True, comment=None),
        sa.Column("byte_count", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("row_count", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("checksum", sa.Text(), nullable=True, comment=None),
        sa.Column("evidence_coverage", sa.Numeric(), nullable=True, comment=None),
        sa.Column("creation_status", sa.Text(), nullable=True, comment=None),
        sa.Column("failure_reason", sa.Text(), nullable=True, comment=None),
        sa.Column("run_id", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.PrimaryKeyConstraint("artifact_id", name="pk_domain_artifact_registry"),
        schema="ctl",
        comment="Run artifact registry for domain investigation family outputs and creation statuses.",
    )
    op.create_table(
        "evaluation_items",
        sa.Column("evaluation_item_id", sa.Text(), nullable=False, comment=None),
        sa.Column("item_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("gold_ref", sa.Text(), nullable=True, comment=None),
        sa.Column("split", sa.Text(), nullable=True, comment=None),
        sa.Column("query_text", sa.Text(), nullable=True, comment=None),
        sa.Column("label", sa.Text(), nullable=True, comment=None),
        sa.Column("dataset_id", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.PrimaryKeyConstraint("evaluation_item_id", name="pk_evaluation_items"),
        schema="eval",
        comment="Frozen evaluation items with gold references, splits, and labels.",
    )
    op.create_table(
        "objects",
        sa.Column("object_id", sa.Text(), nullable=False, comment=None),
        sa.Column("object_type", sa.Text(), nullable=True, comment=None),
        sa.Column("preferred_label", sa.Text(), nullable=True, comment=None),
        sa.Column("lifecycle_state", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("cluster_id", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("object_id", name="pk_objects"),
        schema="kg",
        comment="Canonical knowledge-graph objects with lifecycle and review state.",
    )
    op.create_table(
        "terms",
        sa.Column("term_id", sa.Text(), nullable=False, comment=None),
        sa.Column("uri", sa.Text(), nullable=True, comment=None),
        sa.Column("label", sa.Text(), nullable=True, comment=None),
        sa.Column("kind", sa.Text(), nullable=True, comment=None),
        sa.Column("domain_uri", sa.Text(), nullable=True, comment=None),
        sa.Column("range_uri", sa.Text(), nullable=True, comment=None),
        sa.Column("ontology_version", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.PrimaryKeyConstraint("term_id", name="pk_terms"),
        schema="ontology",
        comment="Controlled ontology terms with URIs, labels, and domain or range constraints.",
    )
    op.create_table(
        "embeddings",
        sa.Column("embedding_id", sa.Text(), nullable=False, comment=None),
        sa.Column("target_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("target_id", sa.Text(), nullable=True, comment=None),
        sa.Column("profile_id", sa.Text(), nullable=True, comment=None),
        sa.Column("dimensions", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("vector_ref", sa.Text(), nullable=True, comment=None),
        sa.Column("model_digest", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("embedding_id", name="pk_embeddings"),
        schema="search",
        comment="Vector embedding references for retrieval targets under a profile.",
    )
    op.create_table(
        "chunks",
        sa.Column("chunk_id", sa.Text(), nullable=False, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("chunker_id", sa.Text(), nullable=True, comment=None),
        sa.Column("ordinal", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("text", sa.Text(), nullable=True, comment=None),
        sa.Column("start_char", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("end_char", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("chunk_id", name="pk_chunks"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_chunks_document_id"),
        schema="corpus",
        comment="Chunker-partitioned text units derived from documents for retrieval and extraction.",
    )
    op.create_table(
        "spans",
        sa.Column("span_id", sa.Text(), nullable=False, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("start_char", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("end_char", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("page", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("kind", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("span_id", name="pk_spans"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_spans_document_id"),
        schema="corpus",
        comment="Character-anchored spans locating evidence within documents.",
    )
    op.create_table(
        "anomaly_findings",
        sa.Column("finding_id", sa.Text(), nullable=False, comment=None),
        sa.Column("finding_type", sa.Text(), nullable=True, comment=None),
        sa.Column("severity", sa.Text(), nullable=True, comment=None),
        sa.Column("status", sa.Text(), nullable=True, comment=None),
        sa.Column("subject_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("rule_id", sa.Text(), nullable=True, comment=None),
        sa.Column("evidence_summary", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.PrimaryKeyConstraint("finding_id", name="pk_anomaly_findings"),
        sa.ForeignKeyConstraint(["subject_object_id"], ["kg.objects.object_id"], name="fk_anomaly_findings_subject_object_id"),
        schema="eval",
        comment="Anomaly findings with severity, status, and evidence summaries for review.",
    )
    op.create_table(
        "aliases",
        sa.Column("alias_id", sa.Text(), nullable=False, comment=None),
        sa.Column("object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("alias_text", sa.Text(), nullable=True, comment=None),
        sa.Column("alias_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("normalized_text", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("alias_id", name="pk_aliases"),
        sa.ForeignKeyConstraint(["object_id"], ["kg.objects.object_id"], name="fk_aliases_object_id"),
        schema="kg",
        comment="Alternate labels and normalized aliases for knowledge-graph objects.",
    )
    op.create_table(
        "bom_lines",
        sa.Column("bom_line_id", sa.Text(), nullable=False, comment=None),
        sa.Column("bom_id", sa.Text(), nullable=True, comment=None),
        sa.Column("root_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("parent_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("child_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("predicate_id", sa.Text(), nullable=True, comment=None),
        sa.Column("listing_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("quantity", sa.Numeric(), nullable=True, comment=None),
        sa.Column("unit", sa.Text(), nullable=True, comment=None),
        sa.Column("alternative_group_id", sa.Text(), nullable=True, comment=None),
        sa.Column("is_mandatory", sa.Boolean(), nullable=True, comment=None),
        sa.Column("effectivity_start", postgresql.TIMESTAMP(timezone=True), nullable=True, comment=None),
        sa.Column("effectivity_end", postgresql.TIMESTAMP(timezone=True), nullable=True, comment=None),
        sa.Column("revision_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("completeness_status", sa.Text(), nullable=True, comment=None),
        sa.Column("cycle_detected", sa.Boolean(), nullable=True, comment=None),
        sa.Column("evidence_fact_ids", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("anchor_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("bom_line_id", name="pk_bom_lines"),
        sa.ForeignKeyConstraint(["child_object_id"], ["kg.objects.object_id"], name="fk_bom_lines_child_object_id"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_bom_lines_document_id"),
        sa.ForeignKeyConstraint(["parent_object_id"], ["kg.objects.object_id"], name="fk_bom_lines_parent_object_id"),
        sa.ForeignKeyConstraint(["revision_object_id"], ["kg.objects.object_id"], name="fk_bom_lines_revision_object_id"),
        sa.ForeignKeyConstraint(["root_object_id"], ["kg.objects.object_id"], name="fk_bom_lines_root_object_id"),
        schema="kg",
        comment="Bill-of-materials hierarchy rows with quantities, alternatives, effectivity, and completeness.",
    )
    op.create_table(
        "catalog_entries",
        sa.Column("catalog_entry_id", sa.Text(), nullable=False, comment=None),
        sa.Column("catalog_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("preferred_name", sa.Text(), nullable=True, comment=None),
        sa.Column("document_count", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("catalog_entry_id", name="pk_catalog_entries"),
        sa.ForeignKeyConstraint(["object_id"], ["kg.objects.object_id"], name="fk_catalog_entries_object_id"),
        schema="kg",
        comment="Catalog entries summarizing objects with preferred names and document counts.",
    )
    op.create_table(
        "invoice_payment_rows",
        sa.Column("row_id", sa.Text(), nullable=False, comment=None),
        sa.Column("row_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("invoice_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("payment_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("line_number", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("amount", sa.Numeric(), nullable=True, comment=None),
        sa.Column("allocated_amount", sa.Numeric(), nullable=True, comment=None),
        sa.Column("currency", sa.Text(), nullable=True, comment=None),
        sa.Column("due_date", postgresql.TIMESTAMP(timezone=True), nullable=True, comment=None),
        sa.Column("payment_date", postgresql.TIMESTAMP(timezone=True), nullable=True, comment=None),
        sa.Column("match_state", sa.Text(), nullable=True, comment=None),
        sa.Column("allocation_group_id", sa.Text(), nullable=True, comment=None),
        sa.Column("debit_credit", sa.Text(), nullable=True, comment=None),
        sa.Column("evidence_fact_ids", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("confidence", sa.Numeric(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("row_id", name="pk_invoice_payment_rows"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_invoice_payment_rows_document_id"),
        sa.ForeignKeyConstraint(["invoice_object_id"], ["kg.objects.object_id"], name="fk_invoice_payment_rows_invoice_object_id"),
        sa.ForeignKeyConstraint(["payment_object_id"], ["kg.objects.object_id"], name="fk_invoice_payment_rows_payment_object_id"),
        schema="kg",
        comment="Invoice lines, payments, credit notes, ledger postings, and allocation match states.",
    )
    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.Text(), nullable=False, comment=None),
        sa.Column("transaction_type", sa.Text(), nullable=True, comment=None),
        sa.Column("amount", sa.Numeric(), nullable=True, comment=None),
        sa.Column("currency", sa.Text(), nullable=True, comment=None),
        sa.Column("party_subject_id", sa.Text(), nullable=True, comment=None),
        sa.Column("party_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("event_time", postgresql.TIMESTAMP(timezone=True), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("transaction_id", name="pk_transactions"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_transactions_document_id"),
        sa.ForeignKeyConstraint(["party_object_id"], ["kg.objects.object_id"], name="fk_transactions_party_object_id"),
        sa.ForeignKeyConstraint(["party_subject_id"], ["kg.objects.object_id"], name="fk_transactions_party_subject_id"),
        schema="kg",
        comment="Financial or exchange transactions linked to parties and source documents.",
    )
    op.create_table(
        "topic_assignments",
        sa.Column("topic_assignment_id", sa.Text(), nullable=False, comment=None),
        sa.Column("topic_id", sa.Text(), nullable=True, comment=None),
        sa.Column("label", sa.Text(), nullable=True, comment=None),
        sa.Column("scheme_id", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("score", sa.Numeric(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("topic_assignment_id", name="pk_topic_assignments"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_topic_assignments_document_id"),
        schema="search",
        comment="Topic assignments linking documents to labeled topics under a scheme.",
    )
    op.create_table(
        "facts",
        sa.Column("fact_id", sa.Text(), nullable=False, comment=None),
        sa.Column("subject_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("predicate_id", sa.Text(), nullable=True, comment=None),
        sa.Column("object_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("literal_value", sa.Text(), nullable=True, comment=None),
        sa.Column("literal_type", sa.Text(), nullable=True, comment=None),
        sa.Column("status", sa.Text(), nullable=True, comment=None),
        sa.Column("confidence", sa.Numeric(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("span_id", sa.Text(), nullable=True, comment=None),
        sa.Column("chunk_id", sa.Text(), nullable=True, comment=None),
        sa.Column("identity_snapshot_id", sa.Text(), nullable=True, comment=None),
        sa.Column("extractor_id", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("fact_id", name="pk_facts"),
        sa.ForeignKeyConstraint(["chunk_id"], ["corpus.chunks.chunk_id"], name="fk_facts_chunk_id"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_facts_document_id"),
        sa.ForeignKeyConstraint(["span_id"], ["corpus.spans.span_id"], name="fk_facts_span_id"),
        sa.ForeignKeyConstraint(["subject_object_id"], ["kg.objects.object_id"], name="fk_facts_subject_object_id"),
        schema="kg",
        comment="Extracted subject-predicate-object facts with evidence anchors and confidence.",
    )
    op.create_table(
        "mentions",
        sa.Column("mention_id", sa.Text(), nullable=False, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("span_id", sa.Text(), nullable=True, comment=None),
        sa.Column("chunk_id", sa.Text(), nullable=True, comment=None),
        sa.Column("surface_form", sa.Text(), nullable=True, comment=None),
        sa.Column("object_anchor_id", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("mention_id", name="pk_mentions"),
        sa.ForeignKeyConstraint(["chunk_id"], ["corpus.chunks.chunk_id"], name="fk_mentions_chunk_id"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_mentions_document_id"),
        sa.ForeignKeyConstraint(["span_id"], ["corpus.spans.span_id"], name="fk_mentions_span_id"),
        schema="kg",
        comment="Surface-form mentions linking documents, spans, and chunks to object anchors.",
    )
    op.create_table(
        "relationship_edges",
        sa.Column("edge_id", sa.Text(), nullable=False, comment=None),
        sa.Column("subject_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("predicate_id", sa.Text(), nullable=True, comment=None),
        sa.Column("object_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("relation_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("direction", sa.Text(), nullable=True, comment=None),
        sa.Column("cardinality", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("inclusion_policy", sa.Text(), nullable=True, comment=None),
        sa.Column("conflict_group_id", sa.Text(), nullable=True, comment=None),
        sa.Column("evidence_fact_ids", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("span_id", sa.Text(), nullable=True, comment=None),
        sa.Column("anchor_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("confidence", sa.Numeric(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("edge_id", name="pk_relationship_edges"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_relationship_edges_document_id"),
        sa.ForeignKeyConstraint(["object_object_id"], ["kg.objects.object_id"], name="fk_relationship_edges_object_object_id"),
        sa.ForeignKeyConstraint(["span_id"], ["corpus.spans.span_id"], name="fk_relationship_edges_span_id"),
        sa.ForeignKeyConstraint(["subject_object_id"], ["kg.objects.object_id"], name="fk_relationship_edges_subject_object_id"),
        schema="kg",
        comment="Typed design/party/product relationship edges with evidence and inclusion state.",
    )
    op.create_table(
        "supply_chain_edges",
        sa.Column("edge_id", sa.Text(), nullable=False, comment=None),
        sa.Column("path_id", sa.Text(), nullable=True, comment=None),
        sa.Column("stage", sa.Text(), nullable=True, comment=None),
        sa.Column("from_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("to_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("role_predicate_id", sa.Text(), nullable=True, comment=None),
        sa.Column("product_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("transaction_id", sa.Text(), nullable=True, comment=None),
        sa.Column("direction", sa.Text(), nullable=True, comment=None),
        sa.Column("event_time", postgresql.TIMESTAMP(timezone=True), nullable=True, comment=None),
        sa.Column("status", sa.Text(), nullable=True, comment=None),
        sa.Column("evidence_fact_ids", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("confidence", sa.Numeric(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column("bucket", sa.Text(), nullable=True, comment="Declared physical partition key from x-arxiv-int.partitionKey."),
        sa.PrimaryKeyConstraint("edge_id", name="pk_supply_chain_edges"),
        sa.ForeignKeyConstraint(["document_id"], ["corpus.documents.document_id"], name="fk_supply_chain_edges_document_id"),
        sa.ForeignKeyConstraint(["from_object_id"], ["kg.objects.object_id"], name="fk_supply_chain_edges_from_object_id"),
        sa.ForeignKeyConstraint(["product_object_id"], ["kg.objects.object_id"], name="fk_supply_chain_edges_product_object_id"),
        sa.ForeignKeyConstraint(["to_object_id"], ["kg.objects.object_id"], name="fk_supply_chain_edges_to_object_id"),
        sa.ForeignKeyConstraint(["transaction_id"], ["kg.transactions.transaction_id"], name="fk_supply_chain_edges_transaction_id"),
        schema="kg",
        comment="Supply-chain stage edges separating quote, order, invoice, ship, receive, and pay claims.",
    )


def downgrade() -> None:
    """Reverse the frozen operations, or refuse when data cannot be restored."""
    op.drop_table("topic_assignments", schema="search")
    op.drop_table("embeddings", schema="search")
    op.drop_table("terms", schema="ontology")
    op.drop_table("transactions", schema="kg")
    op.drop_table("supply_chain_edges", schema="kg")
    op.drop_table("relationship_edges", schema="kg")
    op.drop_table("objects", schema="kg")
    op.drop_table("mentions", schema="kg")
    op.drop_table("invoice_payment_rows", schema="kg")
    op.drop_table("facts", schema="kg")
    op.drop_table("catalog_entries", schema="kg")
    op.drop_table("bom_lines", schema="kg")
    op.drop_table("aliases", schema="kg")
    op.drop_table("evaluation_items", schema="eval")
    op.drop_table("anomaly_findings", schema="eval")
    op.drop_table("domain_artifact_registry", schema="ctl")
    op.drop_table("spans", schema="corpus")
    op.drop_table("source_occurrences", schema="corpus")
    op.drop_table("documents", schema="corpus")
    op.drop_table("chunks", schema="corpus")

"""initial canonical store schema

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
IRREVERSIBLE_REASON: str = "initial store teardown would destroy canonical data"


def schema_metadata() -> sa.MetaData:
    """Return the complete frozen initial table definitions used for creation and inspection."""
    metadata = sa.MetaData()
    sa.Table(
        "documents",
        metadata,
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
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("document_id", name="pk_documents"),
        schema="corpus",
        postgresql_partition_by="HASH (document_id)",
        comment="Normalized document identity and extracted text metadata for the archive corpus.",
    )
    sa.Table(
        "source_occurrences",
        metadata,
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
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("occurrence_id", name="pk_source_occurrences"),
        schema="corpus",
        postgresql_partition_by="HASH (occurrence_id)",
        comment="Silo-relative source locations and scan status for archive bytes.",
    )
    sa.Table(
        "domain_artifact_registry",
        metadata,
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
    sa.Table(
        "evaluation_items",
        metadata,
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
    sa.Table(
        "objects",
        metadata,
        sa.Column("object_id", sa.Text(), nullable=False, comment=None),
        sa.Column("object_type", sa.Text(), nullable=True, comment=None),
        sa.Column("preferred_label", sa.Text(), nullable=True, comment=None),
        sa.Column("lifecycle_state", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("cluster_id", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("object_id", name="pk_objects"),
        schema="kg",
        postgresql_partition_by="HASH (object_id)",
        comment="Canonical knowledge-graph objects with lifecycle and review state.",
    )
    sa.Table(
        "terms",
        metadata,
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
    sa.Table(
        "embeddings",
        metadata,
        sa.Column("embedding_id", sa.Text(), nullable=False, comment=None),
        sa.Column("target_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("target_id", sa.Text(), nullable=True, comment=None),
        sa.Column("profile_id", sa.Text(), nullable=True, comment=None),
        sa.Column("dimensions", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("vector_ref", sa.Text(), nullable=True, comment=None),
        sa.Column("model_digest", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("embedding_id", name="pk_embeddings"),
        schema="search",
        postgresql_partition_by="HASH (embedding_id)",
        comment="Vector embedding references for retrieval targets under a profile.",
    )
    sa.Table(
        "chunks",
        metadata,
        sa.Column("chunk_id", sa.Text(), nullable=False, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("chunker_id", sa.Text(), nullable=True, comment=None),
        sa.Column("ordinal", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("text", sa.Text(), nullable=True, comment=None),
        sa.Column("start_char", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("end_char", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("chunk_id", name="pk_chunks"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_chunks_document_id",
        ),
        schema="corpus",
        postgresql_partition_by="HASH (chunk_id)",
        comment="Chunker-partitioned text units derived from documents for retrieval and extraction.",
    )
    sa.Table(
        "spans",
        metadata,
        sa.Column("span_id", sa.Text(), nullable=False, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("start_char", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("end_char", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("page", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("kind", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("span_id", name="pk_spans"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_spans_document_id",
        ),
        schema="corpus",
        postgresql_partition_by="HASH (span_id)",
        comment="Character-anchored spans locating evidence within documents.",
    )
    sa.Table(
        "anomaly_findings",
        metadata,
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
        sa.ForeignKeyConstraint(
            ["subject_object_id"],
            ["kg.objects.object_id"],
            name="fk_anomaly_findings_subject_object_id",
        ),
        schema="eval",
        comment="Anomaly findings with severity, status, and evidence summaries for review.",
    )
    sa.Table(
        "aliases",
        metadata,
        sa.Column("alias_id", sa.Text(), nullable=False, comment=None),
        sa.Column("object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("alias_text", sa.Text(), nullable=True, comment=None),
        sa.Column("alias_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("normalized_text", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("alias_id", name="pk_aliases"),
        sa.ForeignKeyConstraint(
            ["object_id"], ["kg.objects.object_id"], name="fk_aliases_object_id"
        ),
        schema="kg",
        postgresql_partition_by="HASH (alias_id)",
        comment="Alternate labels and normalized aliases for knowledge-graph objects.",
    )
    sa.Table(
        "bom_lines",
        metadata,
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
        sa.Column(
            "effectivity_start",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment=None,
        ),
        sa.Column(
            "effectivity_end",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment=None,
        ),
        sa.Column("revision_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("completeness_status", sa.Text(), nullable=True, comment=None),
        sa.Column("cycle_detected", sa.Boolean(), nullable=True, comment=None),
        sa.Column("evidence_fact_ids", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("anchor_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("bom_line_id", name="pk_bom_lines"),
        sa.ForeignKeyConstraint(
            ["child_object_id"],
            ["kg.objects.object_id"],
            name="fk_bom_lines_child_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_bom_lines_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["parent_object_id"],
            ["kg.objects.object_id"],
            name="fk_bom_lines_parent_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["revision_object_id"],
            ["kg.objects.object_id"],
            name="fk_bom_lines_revision_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["root_object_id"],
            ["kg.objects.object_id"],
            name="fk_bom_lines_root_object_id",
        ),
        schema="kg",
        postgresql_partition_by="HASH (bom_line_id)",
        comment="Bill-of-materials hierarchy rows with quantities, alternatives, effectivity, and completeness.",
    )
    sa.Table(
        "catalog_entries",
        metadata,
        sa.Column("catalog_entry_id", sa.Text(), nullable=False, comment=None),
        sa.Column("catalog_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("preferred_name", sa.Text(), nullable=True, comment=None),
        sa.Column("document_count", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("catalog_entry_id", name="pk_catalog_entries"),
        sa.ForeignKeyConstraint(
            ["object_id"], ["kg.objects.object_id"], name="fk_catalog_entries_object_id"
        ),
        schema="kg",
        postgresql_partition_by="HASH (catalog_entry_id)",
        comment="Catalog entries summarizing objects with preferred names and document counts.",
    )
    sa.Table(
        "invoice_payment_rows",
        metadata,
        sa.Column("row_id", sa.Text(), nullable=False, comment=None),
        sa.Column("row_kind", sa.Text(), nullable=True, comment=None),
        sa.Column("invoice_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("payment_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("line_number", sa.BigInteger(), nullable=True, comment=None),
        sa.Column("amount", sa.Numeric(), nullable=True, comment=None),
        sa.Column("allocated_amount", sa.Numeric(), nullable=True, comment=None),
        sa.Column("currency", sa.Text(), nullable=True, comment=None),
        sa.Column(
            "due_date", postgresql.TIMESTAMP(timezone=True), nullable=True, comment=None
        ),
        sa.Column(
            "payment_date",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment=None,
        ),
        sa.Column("match_state", sa.Text(), nullable=True, comment=None),
        sa.Column("allocation_group_id", sa.Text(), nullable=True, comment=None),
        sa.Column("debit_credit", sa.Text(), nullable=True, comment=None),
        sa.Column("evidence_fact_ids", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("confidence", sa.Numeric(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("row_id", name="pk_invoice_payment_rows"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_invoice_payment_rows_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["invoice_object_id"],
            ["kg.objects.object_id"],
            name="fk_invoice_payment_rows_invoice_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["payment_object_id"],
            ["kg.objects.object_id"],
            name="fk_invoice_payment_rows_payment_object_id",
        ),
        schema="kg",
        postgresql_partition_by="HASH (row_id)",
        comment="Invoice lines, payments, credit notes, ledger postings, and allocation match states.",
    )
    sa.Table(
        "transactions",
        metadata,
        sa.Column("transaction_id", sa.Text(), nullable=False, comment=None),
        sa.Column("transaction_type", sa.Text(), nullable=True, comment=None),
        sa.Column("amount", sa.Numeric(), nullable=True, comment=None),
        sa.Column("currency", sa.Text(), nullable=True, comment=None),
        sa.Column("party_subject_id", sa.Text(), nullable=True, comment=None),
        sa.Column("party_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column(
            "event_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment=None,
        ),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("transaction_id", name="pk_transactions"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_transactions_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["party_object_id"],
            ["kg.objects.object_id"],
            name="fk_transactions_party_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["party_subject_id"],
            ["kg.objects.object_id"],
            name="fk_transactions_party_subject_id",
        ),
        schema="kg",
        postgresql_partition_by="HASH (transaction_id)",
        comment="Financial or exchange transactions linked to parties and source documents.",
    )
    sa.Table(
        "topic_assignments",
        metadata,
        sa.Column("topic_assignment_id", sa.Text(), nullable=False, comment=None),
        sa.Column("topic_id", sa.Text(), nullable=True, comment=None),
        sa.Column("label", sa.Text(), nullable=True, comment=None),
        sa.Column("scheme_id", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("score", sa.Numeric(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("topic_assignment_id", name="pk_topic_assignments"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_topic_assignments_document_id",
        ),
        schema="search",
        postgresql_partition_by="HASH (topic_assignment_id)",
        comment="Topic assignments linking documents to labeled topics under a scheme.",
    )
    sa.Table(
        "facts",
        metadata,
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
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("fact_id", name="pk_facts"),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["corpus.chunks.chunk_id"], name="fk_facts_chunk_id"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_facts_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["span_id"], ["corpus.spans.span_id"], name="fk_facts_span_id"
        ),
        sa.ForeignKeyConstraint(
            ["subject_object_id"],
            ["kg.objects.object_id"],
            name="fk_facts_subject_object_id",
        ),
        schema="kg",
        postgresql_partition_by="HASH (fact_id)",
        comment="Extracted subject-predicate-object facts with evidence anchors and confidence.",
    )
    sa.Table(
        "mentions",
        metadata,
        sa.Column("mention_id", sa.Text(), nullable=False, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("span_id", sa.Text(), nullable=True, comment=None),
        sa.Column("chunk_id", sa.Text(), nullable=True, comment=None),
        sa.Column("surface_form", sa.Text(), nullable=True, comment=None),
        sa.Column("object_anchor_id", sa.Text(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("mention_id", name="pk_mentions"),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["corpus.chunks.chunk_id"], name="fk_mentions_chunk_id"
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_mentions_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["span_id"], ["corpus.spans.span_id"], name="fk_mentions_span_id"
        ),
        schema="kg",
        postgresql_partition_by="HASH (mention_id)",
        comment="Surface-form mentions linking documents, spans, and chunks to object anchors.",
    )
    sa.Table(
        "relationship_edges",
        metadata,
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
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("edge_id", name="pk_relationship_edges"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_relationship_edges_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["object_object_id"],
            ["kg.objects.object_id"],
            name="fk_relationship_edges_object_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["span_id"], ["corpus.spans.span_id"], name="fk_relationship_edges_span_id"
        ),
        sa.ForeignKeyConstraint(
            ["subject_object_id"],
            ["kg.objects.object_id"],
            name="fk_relationship_edges_subject_object_id",
        ),
        schema="kg",
        postgresql_partition_by="HASH (edge_id)",
        comment="Typed design/party/product relationship edges with evidence and inclusion state.",
    )
    sa.Table(
        "supply_chain_edges",
        metadata,
        sa.Column("edge_id", sa.Text(), nullable=False, comment=None),
        sa.Column("path_id", sa.Text(), nullable=True, comment=None),
        sa.Column("stage", sa.Text(), nullable=True, comment=None),
        sa.Column("from_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("to_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("role_predicate_id", sa.Text(), nullable=True, comment=None),
        sa.Column("product_object_id", sa.Text(), nullable=True, comment=None),
        sa.Column("transaction_id", sa.Text(), nullable=True, comment=None),
        sa.Column("direction", sa.Text(), nullable=True, comment=None),
        sa.Column(
            "event_time",
            postgresql.TIMESTAMP(timezone=True),
            nullable=True,
            comment=None,
        ),
        sa.Column("status", sa.Text(), nullable=True, comment=None),
        sa.Column("evidence_fact_ids", sa.Text(), nullable=True, comment=None),
        sa.Column("document_id", sa.Text(), nullable=True, comment=None),
        sa.Column("review_state", sa.Text(), nullable=True, comment=None),
        sa.Column("confidence", sa.Numeric(), nullable=True, comment=None),
        sa.Column("generation_id", sa.Text(), nullable=False, comment=None),
        sa.Column("contract_version", sa.Text(), nullable=False, comment=None),
        sa.Column(
            "bucket",
            sa.Text(),
            nullable=True,
            comment="Declared physical partition key from x-arxiv-int.partitionKey.",
        ),
        sa.PrimaryKeyConstraint("edge_id", name="pk_supply_chain_edges"),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["corpus.documents.document_id"],
            name="fk_supply_chain_edges_document_id",
        ),
        sa.ForeignKeyConstraint(
            ["from_object_id"],
            ["kg.objects.object_id"],
            name="fk_supply_chain_edges_from_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["product_object_id"],
            ["kg.objects.object_id"],
            name="fk_supply_chain_edges_product_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["to_object_id"],
            ["kg.objects.object_id"],
            name="fk_supply_chain_edges_to_object_id",
        ),
        sa.ForeignKeyConstraint(
            ["transaction_id"],
            ["kg.transactions.transaction_id"],
            name="fk_supply_chain_edges_transaction_id",
        ),
        schema="kg",
        postgresql_partition_by="HASH (edge_id)",
        comment="Supply-chain stage edges separating quote, order, invoice, ship, receive, and pay claims.",
    )
    _store_metadata(metadata)
    return metadata


_PARTITIONED: tuple[tuple[str, str, str], ...] = (
    ("corpus", "chunks", "chunk_id"),
    ("corpus", "documents", "document_id"),
    ("corpus", "source_occurrences", "occurrence_id"),
    ("corpus", "spans", "span_id"),
    ("kg", "aliases", "alias_id"),
    ("kg", "bom_lines", "bom_line_id"),
    ("kg", "catalog_entries", "catalog_entry_id"),
    ("kg", "facts", "fact_id"),
    ("kg", "invoice_payment_rows", "row_id"),
    ("kg", "mentions", "mention_id"),
    ("kg", "objects", "object_id"),
    ("kg", "relationship_edges", "edge_id"),
    ("kg", "supply_chain_edges", "edge_id"),
    ("kg", "transactions", "transaction_id"),
    ("search", "embeddings", "embedding_id"),
    ("search", "topic_assignments", "topic_assignment_id"),
)

STORE_SQL: tuple[str, ...] = (
    "CREATE OR REPLACE FUNCTION ctl.partition_bucket(key text) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ SELECT ((('x' || left(encode(sha256(convert_to(key, 'UTF8')), 'hex'), 7))::bit(28)::int) % 16)::text $$;",
    "CREATE OR REPLACE FUNCTION search.enforce_embedding_profile() RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE profile RECORD; BEGIN IF NEW.profile_id IS NULL THEN RETURN NEW; END IF; SELECT * INTO profile FROM search.embedding_profiles WHERE profile_id = NEW.profile_id; IF NOT FOUND THEN RAISE EXCEPTION 'unknown embedding profile %', NEW.profile_id; END IF; IF NEW.dimensions IS DISTINCT FROM profile.dimensions THEN RAISE EXCEPTION 'embedding dimensions mix profile %', NEW.profile_id; END IF; IF NEW.model_digest IS DISTINCT FROM profile.model_digest THEN RAISE EXCEPTION 'embedding model digest mix profile %', NEW.profile_id; END IF; IF EXISTS (SELECT 1 FROM search.embeddings e WHERE e.embedding_id <> NEW.embedding_id AND e.target_kind IS NOT DISTINCT FROM NEW.target_kind AND e.target_id IS NOT DISTINCT FROM NEW.target_id AND e.profile_id IS NOT DISTINCT FROM NEW.profile_id) THEN RAISE EXCEPTION 'duplicate embedding target for profile %', NEW.profile_id; END IF; RETURN NEW; END; $$;",
    "CREATE TRIGGER trg_embeddings_profile BEFORE INSERT OR UPDATE ON search.embeddings FOR EACH ROW EXECUTE FUNCTION search.enforce_embedding_profile()",
    "GRANT arxiv_int_migrator, arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader TO CURRENT_USER",
    "GRANT USAGE ON SCHEMA corpus, ctl, eval, kg, ontology, search TO arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader",
    "GRANT USAGE, CREATE ON SCHEMA staging TO arxiv_int_pipeline",
    "GRANT USAGE ON SCHEMA staging TO arxiv_int_reader",
    "GRANT USAGE, CREATE ON SCHEMA derived TO arxiv_int_dbt",
    "GRANT USAGE ON SCHEMA derived TO arxiv_int_reader",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA corpus, ctl, eval, kg, ontology, search TO arxiv_int_pipeline",
    "GRANT SELECT ON ALL TABLES IN SCHEMA corpus, ctl, eval, kg, ontology, search TO arxiv_int_dbt, arxiv_int_reader",
    "GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA staging TO arxiv_int_pipeline",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON search.embedding_profiles TO arxiv_int_pipeline",
    "GRANT SELECT ON search.embedding_profiles TO arxiv_int_dbt, arxiv_int_reader",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA corpus, ctl, eval, kg, ontology, search GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO arxiv_int_pipeline",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA corpus, ctl, eval, kg, ontology, search GRANT SELECT ON TABLES TO arxiv_int_dbt, arxiv_int_reader",
    "ALTER DEFAULT PRIVILEGES IN SCHEMA derived GRANT SELECT ON TABLES TO arxiv_int_reader",
    "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA corpus, ctl, eval, kg, ontology, search FROM arxiv_int_dbt",
    "REVOKE ALL ON TABLE public.alembic_version FROM arxiv_int_dbt, arxiv_int_pipeline, arxiv_int_reader",
    "GRANT SELECT ON TABLE public.alembic_version TO arxiv_int_reader",
    "GRANT SELECT, INSERT, UPDATE, DELETE ON ctl.projections, ctl.projection_active, ctl.projection_evidence, ctl.projection_cleanup TO arxiv_int_pipeline",
    "GRANT SELECT ON ctl.projections, ctl.projection_active, ctl.projection_evidence, ctl.projection_cleanup TO arxiv_int_dbt, arxiv_int_reader",
    "GRANT USAGE, CREATE ON SCHEMA search TO arxiv_int_pipeline",
)

STORE_ROLES: tuple[str, ...] = (
    "arxiv_int_migrator",
    "arxiv_int_pipeline",
    "arxiv_int_dbt",
    "arxiv_int_reader",
)
STORE_SCHEMAS: tuple[str, ...] = (
    "corpus",
    "ctl",
    "eval",
    "kg",
    "ontology",
    "search",
    "staging",
    "derived",
)


def _store_metadata(metadata: sa.MetaData) -> None:
    canonical = tuple(metadata.tables.values())
    facts = metadata.tables["kg.facts"]
    for name, expression in (
        (
            "ck_facts_subject_predicate",
            "subject_object_id IS NOT NULL AND predicate_id IS NOT NULL",
        ),
        (
            "ck_facts_object_xor_literal",
            "(object_object_id IS NOT NULL AND literal_value IS NULL AND literal_type IS NULL) OR (object_object_id IS NULL AND literal_value IS NOT NULL AND literal_type IS NOT NULL)",
        ),
        ("ck_facts_provenance", "document_id IS NOT NULL AND extractor_id IS NOT NULL"),
        (
            "ck_facts_status",
            "status IN ('proposed', 'accepted', 'rejected', 'superseded', 'conflicted')",
        ),
    ):
        facts.append_constraint(sa.CheckConstraint(expression, name=name))
    for name in ("subject_object_id", "status", "document_id"):
        sa.Index(f"ix_facts_{name}", facts.c[name])
    sa.Table(
        "embedding_profiles",
        metadata,
        sa.Column("profile_id", sa.Text(), primary_key=True),
        sa.Column("dimensions", sa.BigInteger(), nullable=False),
        sa.Column("model_digest", sa.Text(), nullable=False),
        sa.Column("pooling", sa.Text()),
        sa.Column("normalization", sa.Text()),
        sa.Column("chunker_id", sa.Text()),
        sa.Column("contract_version", sa.Text(), nullable=False),
        schema="search",
    )
    embeddings = metadata.tables["search.embeddings"]
    embeddings.append_constraint(
        sa.ForeignKeyConstraint(
            ["profile_id"],
            ["search.embedding_profiles.profile_id"],
            name="fk_embeddings_profile",
        )
    )
    sa.Index("ix_embeddings_profile_id", embeddings.c.profile_id)
    for table in canonical:
        sa.Table(
            table.name,
            metadata,
            *(
                sa.Column(
                    column.name,
                    column.type,
                    nullable=column.nullable,
                    comment=column.comment,
                )
                for column in table.columns
            ),
            schema="staging",
            prefixes=["UNLOGGED"],
        )
    _projection_metadata(metadata)


def _projection_metadata(metadata: sa.MetaData) -> None:
    table = sa.Table(
        "projections",
        metadata,
        sa.Column("projection_id", sa.Text(), primary_key=True),
        *(
            sa.Column(name, sa.Text(), nullable=False)
            for name in (
                "kind",
                "version_id",
                "status",
                "schema_version",
                "engine",
                "run_id",
            )
        ),
        *(
            sa.Column(name, sa.Text())
            for name in (
                "engine_object",
                "input_fingerprint",
                "checksum",
                "quality_status",
                "last_committed_id",
                "canonical_fact_version",
            )
        ),
        sa.Column("row_count", sa.BigInteger()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kind IN ('lexical', 'vector', 'graph')", name="ck_projections_kind"
        ),
        sa.CheckConstraint(
            "status IN ('staging', 'validated', 'active', 'failed', 'retired', 'dropped')",
            name="ck_projections_status",
        ),
        sa.UniqueConstraint("kind", "version_id", name="uq_projections_kind_version"),
        schema="ctl",
    )
    sa.Index("ix_projections_kind_status", table.c.kind, table.c.status)
    sa.Table(
        "projection_active",
        metadata,
        sa.Column("kind", sa.Text(), primary_key=True),
        sa.Column(
            "projection_id",
            sa.Text(),
            sa.ForeignKey("ctl.projections.projection_id"),
            nullable=False,
        ),
        sa.Column("previous_projection_id", sa.Text()),
        sa.Column(
            "switched_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "kind IN ('lexical', 'vector', 'graph')", name="ck_projection_active_kind"
        ),
        schema="ctl",
    )
    evidence = sa.Table(
        "projection_evidence",
        metadata,
        sa.Column("evidence_id", sa.Text(), primary_key=True),
        sa.Column(
            "projection_id",
            sa.Text(),
            sa.ForeignKey("ctl.projections.projection_id"),
            nullable=False,
        ),
        sa.Column("check_name", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("detail", sa.Text()),
        sa.Column("checked_count", sa.BigInteger()),
        sa.Column("failed_count", sa.BigInteger()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        schema="ctl",
    )
    sa.Index("ix_projection_evidence_projection_id", evidence.c.projection_id)
    sa.Table(
        "projection_cleanup",
        metadata,
        sa.Column("cleanup_id", sa.Text(), primary_key=True),
        sa.Column(
            "projection_id",
            sa.Text(),
            sa.ForeignKey("ctl.projections.projection_id"),
            nullable=False,
        ),
        sa.Column("engine_object", sa.Text()),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column(
            "planned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "status IN ('planned', 'executed', 'skipped')",
            name="ck_projection_cleanup_status",
        ),
        schema="ctl",
    )


def upgrade() -> None:
    """Create the complete initial store directly, without historical table conversions."""
    for schema in STORE_SCHEMAS:
        op.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
    for role in STORE_ROLES:
        op.execute(
            "DO $body$ BEGIN "
            f"IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
            f"CREATE ROLE {role} NOLOGIN; END IF; END $body$;"
        )
    for definition in schema_metadata().sorted_tables:
        op.execute(sa.schema.CreateTable(definition))
        for index in sorted(definition.indexes, key=lambda item: str(item.name)):
            op.execute(sa.schema.CreateIndex(index))
    for schema, table, _key in _PARTITIONED:
        for remainder in range(16):
            op.execute(
                f"CREATE TABLE {schema}.{table}_p{remainder:02d} PARTITION OF {schema}.{table} "
                f"FOR VALUES WITH (MODULUS 16, REMAINDER {remainder})"
            )
    for statement in STORE_SQL:
        op.execute(statement)


def downgrade() -> None:
    """Refuse a teardown that would destroy canonical data."""
    raise RuntimeError(IRREVERSIBLE_REASON)

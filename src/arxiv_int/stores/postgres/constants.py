"""Named identities for the canonical PostgreSQL store overlay.

Revisions freeze the same names as SQL literals. Changing a value here
does not change an applied revision; add a new revision instead.
"""

CANONICAL_SCHEMAS: tuple[str, ...] = ("corpus", "ctl", "eval", "kg", "ontology", "search")
STAGING_SCHEMA = "staging"
DERIVED_SCHEMA = "derived"
STORE_SCHEMAS: tuple[str, ...] = (*CANONICAL_SCHEMAS, STAGING_SCHEMA, DERIVED_SCHEMA)

ROLE_MIGRATOR = "arxiv_int_migrator"
ROLE_PIPELINE = "arxiv_int_pipeline"
ROLE_DBT = "arxiv_int_dbt"
ROLE_READER = "arxiv_int_reader"
STORE_ROLES: tuple[str, ...] = (ROLE_MIGRATOR, ROLE_PIPELINE, ROLE_DBT, ROLE_READER)

HASH_MODULUS = 16
BUCKET_FUNCTION = "ctl.partition_bucket"

# Physical HASH key is the logical primary key so foreign keys stay valid.
PARTITIONED_TABLES: tuple[tuple[str, str, str], ...] = (
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

OWNED_TABLES: tuple[tuple[str, str], ...] = (
    ("corpus", "chunks"),
    ("corpus", "documents"),
    ("corpus", "source_occurrences"),
    ("corpus", "spans"),
    ("ctl", "domain_artifact_registry"),
    ("eval", "anomaly_findings"),
    ("eval", "evaluation_items"),
    ("kg", "aliases"),
    ("kg", "bom_lines"),
    ("kg", "catalog_entries"),
    ("kg", "facts"),
    ("kg", "invoice_payment_rows"),
    ("kg", "mentions"),
    ("kg", "objects"),
    ("kg", "relationship_edges"),
    ("kg", "supply_chain_edges"),
    ("kg", "transactions"),
    ("ontology", "terms"),
    ("search", "embeddings"),
    ("search", "topic_assignments"),
)

FOREIGN_KEYS: tuple[tuple[str, str, str, str, str, str, str], ...] = (
    (
        "corpus",
        "chunks",
        "fk_chunks_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
    (
        "corpus",
        "spans",
        "fk_spans_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
    (
        "eval",
        "anomaly_findings",
        "fk_anomaly_findings_subject_object_id",
        "subject_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    ("kg", "aliases", "fk_aliases_object_id", "object_id", "kg", "objects", "object_id"),
    (
        "kg",
        "bom_lines",
        "fk_bom_lines_child_object_id",
        "child_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "bom_lines",
        "fk_bom_lines_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
    (
        "kg",
        "bom_lines",
        "fk_bom_lines_parent_object_id",
        "parent_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "bom_lines",
        "fk_bom_lines_revision_object_id",
        "revision_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "bom_lines",
        "fk_bom_lines_root_object_id",
        "root_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "catalog_entries",
        "fk_catalog_entries_object_id",
        "object_id",
        "kg",
        "objects",
        "object_id",
    ),
    ("kg", "facts", "fk_facts_chunk_id", "chunk_id", "corpus", "chunks", "chunk_id"),
    ("kg", "facts", "fk_facts_document_id", "document_id", "corpus", "documents", "document_id"),
    ("kg", "facts", "fk_facts_span_id", "span_id", "corpus", "spans", "span_id"),
    (
        "kg",
        "facts",
        "fk_facts_subject_object_id",
        "subject_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "invoice_payment_rows",
        "fk_invoice_payment_rows_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
    (
        "kg",
        "invoice_payment_rows",
        "fk_invoice_payment_rows_invoice_object_id",
        "invoice_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "invoice_payment_rows",
        "fk_invoice_payment_rows_payment_object_id",
        "payment_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    ("kg", "mentions", "fk_mentions_chunk_id", "chunk_id", "corpus", "chunks", "chunk_id"),
    (
        "kg",
        "mentions",
        "fk_mentions_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
    ("kg", "mentions", "fk_mentions_span_id", "span_id", "corpus", "spans", "span_id"),
    (
        "kg",
        "relationship_edges",
        "fk_relationship_edges_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
    (
        "kg",
        "relationship_edges",
        "fk_relationship_edges_object_object_id",
        "object_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "relationship_edges",
        "fk_relationship_edges_span_id",
        "span_id",
        "corpus",
        "spans",
        "span_id",
    ),
    (
        "kg",
        "relationship_edges",
        "fk_relationship_edges_subject_object_id",
        "subject_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_from_object_id",
        "from_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_product_object_id",
        "product_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_to_object_id",
        "to_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_transaction_id",
        "transaction_id",
        "kg",
        "transactions",
        "transaction_id",
    ),
    (
        "kg",
        "transactions",
        "fk_transactions_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
    (
        "kg",
        "transactions",
        "fk_transactions_party_object_id",
        "party_object_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "kg",
        "transactions",
        "fk_transactions_party_subject_id",
        "party_subject_id",
        "kg",
        "objects",
        "object_id",
    ),
    (
        "search",
        "topic_assignments",
        "fk_topic_assignments_document_id",
        "document_id",
        "corpus",
        "documents",
        "document_id",
    ),
)

FACT_STATUSES: tuple[str, ...] = (
    "proposed",
    "accepted",
    "rejected",
    "superseded",
    "conflicted",
)

EMBEDDING_PROFILES_TABLE = "search.embedding_profiles"
ALEMBIC_VERSION_TABLE = "alembic_version"
HEAD_REVISION = "0003"
PARTITION_OVERLAY_REVISION = "0002"
PROJECTION_METADATA_TABLES: tuple[str, ...] = (
    "projections",
    "projection_active",
    "projection_evidence",
    "projection_cleanup",
)

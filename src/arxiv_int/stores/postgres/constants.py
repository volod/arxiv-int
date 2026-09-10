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
    ("corpus", "document_path_event", "event_id"),
    ("corpus", "documents", "document_id"),
    ("corpus", "duplicate_groups", "duplicate_membership_id"),
    ("corpus", "normalized_documents", "normalized_document_id"),
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
    ("corpus", "document_path_event"),
    ("corpus", "documents"),
    ("corpus", "duplicate_groups"),
    ("corpus", "normalized_documents"),
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

FACT_STATUSES: tuple[str, ...] = (
    "proposed",
    "accepted",
    "rejected",
    "superseded",
    "conflicted",
)

EMBEDDING_PROFILES_TABLE = "search.embedding_profiles"
ALEMBIC_VERSION_TABLE = "alembic_version"
HEAD_REVISION = "0001"
INITIAL_REVISION = "0001"
PROJECTION_METADATA_TABLES: tuple[str, ...] = (
    "projections",
    "projection_active",
    "projection_evidence",
    "projection_cleanup",
)
LEDGER_TABLES: tuple[str, ...] = (
    "run",
    "stage_run",
    "shard_run",
    "reuse_lease",
    "checkpoint",
    "shard_error",
    "artifact_manifest",
    "artifact_lineage",
    "resource_lease",
)
PROGRESS_TABLES: tuple[str, ...] = ("stage_progress",)
RECONCILE_TABLES: tuple[str, ...] = (
    "source_tombstone",
    "prune_event",
    "artifact_pin",
)
CONTROL_TABLES: tuple[str, ...] = (
    *PROJECTION_METADATA_TABLES,
    *LEDGER_TABLES,
    *PROGRESS_TABLES,
    *RECONCILE_TABLES,
)

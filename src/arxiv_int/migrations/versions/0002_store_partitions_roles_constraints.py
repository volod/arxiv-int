"""store partitions, roles, constraints, and staging

Generated for the canonical store overlay. Definitions below are frozen:
this revision never imports today's contracts to decide what it creates.

Revision ID: 0002
Revises: 0001
Contract fingerprints: unchanged from 0001; this revision adds store objects.
"""

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {}
REVIEW_NOTES: tuple[str, ...] = (
    "HASH partitions use the logical primary key so foreign keys stay valid",
    "application bucket values use ctl.partition_bucket (SHA-256 prefix)",
    "dbt may CREATE in derived only; canonical writes stay with arxiv_int_pipeline",
)
IRREVERSIBLE_REASON: str = ""

_HASH_MODULUS = 16
_PARTITIONED = (
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
_OWNED = (
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
_FOREIGN_KEYS = (
    ("corpus", "chunks", "fk_chunks_document_id", "document_id", "corpus.documents.document_id"),
    ("corpus", "spans", "fk_spans_document_id", "document_id", "corpus.documents.document_id"),
    (
        "eval",
        "anomaly_findings",
        "fk_anomaly_findings_subject_object_id",
        "subject_object_id",
        "kg.objects.object_id",
    ),
    ("kg", "aliases", "fk_aliases_object_id", "object_id", "kg.objects.object_id"),
    ("kg", "bom_lines", "fk_bom_lines_child_object_id", "child_object_id", "kg.objects.object_id"),
    ("kg", "bom_lines", "fk_bom_lines_document_id", "document_id", "corpus.documents.document_id"),
    ("kg", "bom_lines", "fk_bom_lines_parent_object_id", "parent_object_id", "kg.objects.object_id"),
    (
        "kg",
        "bom_lines",
        "fk_bom_lines_revision_object_id",
        "revision_object_id",
        "kg.objects.object_id",
    ),
    ("kg", "bom_lines", "fk_bom_lines_root_object_id", "root_object_id", "kg.objects.object_id"),
    ("kg", "catalog_entries", "fk_catalog_entries_object_id", "object_id", "kg.objects.object_id"),
    ("kg", "facts", "fk_facts_chunk_id", "chunk_id", "corpus.chunks.chunk_id"),
    ("kg", "facts", "fk_facts_document_id", "document_id", "corpus.documents.document_id"),
    ("kg", "facts", "fk_facts_span_id", "span_id", "corpus.spans.span_id"),
    ("kg", "facts", "fk_facts_subject_object_id", "subject_object_id", "kg.objects.object_id"),
    (
        "kg",
        "invoice_payment_rows",
        "fk_invoice_payment_rows_document_id",
        "document_id",
        "corpus.documents.document_id",
    ),
    (
        "kg",
        "invoice_payment_rows",
        "fk_invoice_payment_rows_invoice_object_id",
        "invoice_object_id",
        "kg.objects.object_id",
    ),
    (
        "kg",
        "invoice_payment_rows",
        "fk_invoice_payment_rows_payment_object_id",
        "payment_object_id",
        "kg.objects.object_id",
    ),
    ("kg", "mentions", "fk_mentions_chunk_id", "chunk_id", "corpus.chunks.chunk_id"),
    ("kg", "mentions", "fk_mentions_document_id", "document_id", "corpus.documents.document_id"),
    ("kg", "mentions", "fk_mentions_span_id", "span_id", "corpus.spans.span_id"),
    (
        "kg",
        "relationship_edges",
        "fk_relationship_edges_document_id",
        "document_id",
        "corpus.documents.document_id",
    ),
    (
        "kg",
        "relationship_edges",
        "fk_relationship_edges_object_object_id",
        "object_object_id",
        "kg.objects.object_id",
    ),
    ("kg", "relationship_edges", "fk_relationship_edges_span_id", "span_id", "corpus.spans.span_id"),
    (
        "kg",
        "relationship_edges",
        "fk_relationship_edges_subject_object_id",
        "subject_object_id",
        "kg.objects.object_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_document_id",
        "document_id",
        "corpus.documents.document_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_from_object_id",
        "from_object_id",
        "kg.objects.object_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_product_object_id",
        "product_object_id",
        "kg.objects.object_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_to_object_id",
        "to_object_id",
        "kg.objects.object_id",
    ),
    (
        "kg",
        "supply_chain_edges",
        "fk_supply_chain_edges_transaction_id",
        "transaction_id",
        "kg.transactions.transaction_id",
    ),
    ("kg", "transactions", "fk_transactions_document_id", "document_id", "corpus.documents.document_id"),
    ("kg", "transactions", "fk_transactions_party_object_id", "party_object_id", "kg.objects.object_id"),
    (
        "kg",
        "transactions",
        "fk_transactions_party_subject_id",
        "party_subject_id",
        "kg.objects.object_id",
    ),
    (
        "search",
        "topic_assignments",
        "fk_topic_assignments_document_id",
        "document_id",
        "corpus.documents.document_id",
    ),
)


def _drop_foreign_keys() -> None:
    for schema, table, name, _column, _target in _FOREIGN_KEYS:
        op.execute(f"ALTER TABLE {schema}.{table} DROP CONSTRAINT {name}")


def _restore_foreign_keys() -> None:
    for schema, table, name, column, target in _FOREIGN_KEYS:
        qualified, _, referenced = target.rpartition(".")
        op.execute(
            f"ALTER TABLE {schema}.{table} ADD CONSTRAINT {name} "
            f"FOREIGN KEY ({column}) REFERENCES {qualified} ({referenced})"
        )


def _hash_partition(schema: str, table: str, pk: str) -> None:
    op.execute(f"ALTER TABLE {schema}.{table} RENAME TO {table}_unpart")
    op.execute(
        f"CREATE TABLE {schema}.{table} (LIKE {schema}.{table}_unpart "
        f"INCLUDING DEFAULTS INCLUDING COMMENTS) PARTITION BY HASH ({pk})"
    )
    op.execute(f"ALTER TABLE {schema}.{table} ADD PRIMARY KEY ({pk})")
    for remainder in range(_HASH_MODULUS):
        op.execute(
            f"CREATE TABLE {schema}.{table}_p{remainder} PARTITION OF {schema}.{table} "
            f"FOR VALUES WITH (MODULUS {_HASH_MODULUS}, REMAINDER {remainder})"
        )
    op.execute(f"INSERT INTO {schema}.{table} SELECT * FROM {schema}.{table}_unpart")
    op.execute(f"DROP TABLE {schema}.{table}_unpart")


def _unhash_partition(schema: str, table: str, pk: str) -> None:
    op.execute(
        f"CREATE TABLE {schema}.{table}_plain (LIKE {schema}.{table} "
        f"INCLUDING DEFAULTS INCLUDING COMMENTS)"
    )
    op.execute(f"ALTER TABLE {schema}.{table}_plain ADD PRIMARY KEY ({pk})")
    op.execute(f"INSERT INTO {schema}.{table}_plain SELECT * FROM {schema}.{table}")
    op.execute(f"DROP TABLE {schema}.{table}")
    op.execute(f"ALTER TABLE {schema}.{table}_plain RENAME TO {table}")


def upgrade() -> None:
    """Apply store partitions, roles, constraints, staging, and grants."""
    for role in ("arxiv_int_migrator", "arxiv_int_pipeline", "arxiv_int_dbt", "arxiv_int_reader"):
        op.execute(
            "DO $body$ BEGIN IF NOT EXISTS "
            f"(SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
            f"CREATE ROLE {role} NOLOGIN; END IF; END $body$;"
        )
    op.execute("CREATE SCHEMA IF NOT EXISTS staging")
    op.execute("CREATE SCHEMA IF NOT EXISTS derived")
    op.execute(
        "CREATE OR REPLACE FUNCTION ctl.partition_bucket(key text) RETURNS text "
        "LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ "
        "SELECT ((('x' || left(encode(sha256(convert_to(key, 'UTF8')), 'hex'), 7))"
        "::bit(28)::int) % 16)::text $$;"
    )
    _drop_foreign_keys()
    for schema, table, pk in _PARTITIONED:
        _hash_partition(schema, table, pk)
    _restore_foreign_keys()
    op.execute(
        "ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_subject_predicate "
        "CHECK (subject_object_id IS NOT NULL AND predicate_id IS NOT NULL)"
    )
    op.execute(
        "ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_object_xor_literal CHECK ("
        "(object_object_id IS NOT NULL AND literal_value IS NULL AND literal_type IS NULL) "
        "OR (object_object_id IS NULL AND literal_value IS NOT NULL AND literal_type IS NOT NULL))"
    )
    op.execute(
        "ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_provenance "
        "CHECK (document_id IS NOT NULL AND extractor_id IS NOT NULL)"
    )
    op.execute(
        "ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_status CHECK (status IN "
        "('proposed', 'accepted', 'rejected', 'superseded', 'conflicted'))"
    )
    op.execute(
        "CREATE TABLE search.embedding_profiles ("
        "profile_id TEXT PRIMARY KEY, dimensions BIGINT NOT NULL, "
        "model_digest TEXT NOT NULL, pooling TEXT, normalization TEXT, "
        "chunker_id TEXT, contract_version TEXT NOT NULL)"
    )
    op.execute(
        "CREATE OR REPLACE FUNCTION search.enforce_embedding_profile() "
        "RETURNS trigger LANGUAGE plpgsql AS $$ DECLARE profile RECORD; BEGIN "
        "IF NEW.profile_id IS NULL THEN RETURN NEW; END IF; "
        "SELECT * INTO profile FROM search.embedding_profiles WHERE profile_id = NEW.profile_id; "
        "IF NOT FOUND THEN RAISE EXCEPTION 'unknown embedding profile %', NEW.profile_id; END IF; "
        "IF NEW.dimensions IS DISTINCT FROM profile.dimensions THEN "
        "RAISE EXCEPTION 'embedding dimensions mix profile %', NEW.profile_id; END IF; "
        "IF NEW.model_digest IS DISTINCT FROM profile.model_digest THEN "
        "RAISE EXCEPTION 'embedding model digest mix profile %', NEW.profile_id; END IF; "
        "IF EXISTS (SELECT 1 FROM search.embeddings e WHERE e.embedding_id <> NEW.embedding_id "
        "AND e.target_kind IS NOT DISTINCT FROM NEW.target_kind "
        "AND e.target_id IS NOT DISTINCT FROM NEW.target_id "
        "AND e.profile_id IS NOT DISTINCT FROM NEW.profile_id) THEN "
        "RAISE EXCEPTION 'duplicate embedding target for profile %', NEW.profile_id; END IF; "
        "RETURN NEW; END; $$;"
    )
    op.execute(
        "CREATE TRIGGER trg_embeddings_profile BEFORE INSERT OR UPDATE ON search.embeddings "
        "FOR EACH ROW EXECUTE FUNCTION search.enforce_embedding_profile()"
    )
    op.execute(
        "ALTER TABLE search.embeddings ADD CONSTRAINT fk_embeddings_profile "
        "FOREIGN KEY (profile_id) REFERENCES search.embedding_profiles (profile_id)"
    )
    op.execute("CREATE INDEX ix_facts_subject_object_id ON kg.facts (subject_object_id)")
    op.execute("CREATE INDEX ix_facts_status ON kg.facts (status)")
    op.execute("CREATE INDEX ix_facts_document_id ON kg.facts (document_id)")
    op.execute("CREATE INDEX ix_embeddings_profile_id ON search.embeddings (profile_id)")
    for schema, table in _OWNED:
        op.execute(
            f"CREATE UNLOGGED TABLE staging.{table} "
            f"(LIKE {schema}.{table} INCLUDING DEFAULTS INCLUDING COMMENTS)"
        )
    op.execute(
        "GRANT arxiv_int_migrator, arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader "
        "TO CURRENT_USER"
    )
    op.execute(
        "GRANT USAGE ON SCHEMA corpus, ctl, eval, kg, ontology, search "
        "TO arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader"
    )
    op.execute("GRANT USAGE, CREATE ON SCHEMA staging TO arxiv_int_pipeline")
    op.execute("GRANT USAGE ON SCHEMA staging TO arxiv_int_reader")
    op.execute("GRANT USAGE, CREATE ON SCHEMA derived TO arxiv_int_dbt")
    op.execute("GRANT USAGE ON SCHEMA derived TO arxiv_int_reader")
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA "
        "corpus, ctl, eval, kg, ontology, search TO arxiv_int_pipeline"
    )
    op.execute(
        "GRANT SELECT ON ALL TABLES IN SCHEMA corpus, ctl, eval, kg, ontology, search "
        "TO arxiv_int_dbt, arxiv_int_reader"
    )
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA staging "
        "TO arxiv_int_pipeline"
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON search.embedding_profiles TO arxiv_int_pipeline")
    op.execute("GRANT SELECT ON search.embedding_profiles TO arxiv_int_dbt, arxiv_int_reader")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA corpus, ctl, eval, kg, ontology, search "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO arxiv_int_pipeline"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA corpus, ctl, eval, kg, ontology, search "
        "GRANT SELECT ON TABLES TO arxiv_int_dbt, arxiv_int_reader"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA derived GRANT SELECT ON TABLES TO arxiv_int_reader"
    )
    op.execute(
        "REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA "
        "corpus, ctl, eval, kg, ontology, search FROM arxiv_int_dbt"
    )
    op.execute(
        "REVOKE ALL ON TABLE public.alembic_version FROM "
        "arxiv_int_dbt, arxiv_int_pipeline, arxiv_int_reader"
    )
    op.execute("GRANT SELECT ON TABLE public.alembic_version TO arxiv_int_reader")


def downgrade() -> None:
    """Restore unpartitioned 0001 tables and drop store-owned objects."""
    op.execute("DROP TRIGGER IF EXISTS trg_embeddings_profile ON search.embeddings")
    op.execute("ALTER TABLE search.embeddings DROP CONSTRAINT IF EXISTS fk_embeddings_profile")
    op.execute("DROP FUNCTION IF EXISTS search.enforce_embedding_profile()")
    op.execute("DROP TABLE IF EXISTS search.embedding_profiles")
    op.execute("DROP INDEX IF EXISTS kg.ix_facts_subject_object_id")
    op.execute("DROP INDEX IF EXISTS kg.ix_facts_status")
    op.execute("DROP INDEX IF EXISTS kg.ix_facts_document_id")
    op.execute("DROP INDEX IF EXISTS search.ix_embeddings_profile_id")
    op.execute("ALTER TABLE kg.facts DROP CONSTRAINT IF EXISTS ck_facts_status")
    op.execute("ALTER TABLE kg.facts DROP CONSTRAINT IF EXISTS ck_facts_provenance")
    op.execute("ALTER TABLE kg.facts DROP CONSTRAINT IF EXISTS ck_facts_object_xor_literal")
    op.execute("ALTER TABLE kg.facts DROP CONSTRAINT IF EXISTS ck_facts_subject_predicate")
    for _schema, table in _OWNED:
        op.execute(f"DROP TABLE IF EXISTS staging.{table}")
    _drop_foreign_keys()
    for schema, table, pk in reversed(_PARTITIONED):
        _unhash_partition(schema, table, pk)
    _restore_foreign_keys()
    op.execute("DROP FUNCTION IF EXISTS ctl.partition_bucket(text)")
    op.execute(
        "REVOKE ALL ON ALL TABLES IN SCHEMA corpus, ctl, eval, kg, ontology, search "
        "FROM arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader"
    )
    op.execute(
        "REVOKE ALL ON ALL TABLES IN SCHEMA staging FROM arxiv_int_pipeline, arxiv_int_reader"
    )
    op.execute(
        "REVOKE ALL ON SCHEMA corpus, ctl, eval, kg, ontology, search, staging, derived "
        "FROM arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader"
    )
    op.execute(
        "REVOKE ALL ON TABLE public.alembic_version FROM "
        "arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA corpus, ctl, eval, kg, ontology, search "
        "REVOKE ALL ON TABLES FROM arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA derived REVOKE ALL ON TABLES FROM arxiv_int_reader"
    )
    op.execute("DROP SCHEMA IF EXISTS staging CASCADE")
    op.execute("DROP SCHEMA IF EXISTS derived RESTRICT")
    op.execute(
        "REVOKE arxiv_int_migrator, arxiv_int_pipeline, arxiv_int_dbt, arxiv_int_reader "
        "FROM CURRENT_USER"
    )
    for role in ("arxiv_int_reader", "arxiv_int_dbt", "arxiv_int_pipeline", "arxiv_int_migrator"):
        op.execute(f"DROP ROLE IF EXISTS {role}")

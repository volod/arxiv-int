"""SQL fragments for roles, staging, constraints, and store-owned objects.

These strings are the operator/runtime copy. Revision 0002 embeds equivalent
frozen SQL and must not import this module.
"""

from arxiv_int.stores.postgres.constants import (
    CANONICAL_SCHEMAS,
    DERIVED_SCHEMA,
    EMBEDDING_PROFILES_TABLE,
    FACT_STATUSES,
    OWNED_TABLES,
    ROLE_DBT,
    ROLE_MIGRATOR,
    ROLE_PIPELINE,
    ROLE_READER,
    STAGING_SCHEMA,
)
from arxiv_int.stores.postgres.hashing import partition_bucket_sql


def create_role_sql(role: str) -> str:
    """Return idempotent NOLOGIN role creation."""
    return (
        "DO $body$ BEGIN "
        f"IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
        f"CREATE ROLE {role} NOLOGIN; "
        "END IF; END $body$;"
    )


def bucket_function_sql() -> str:
    """Return CREATE FUNCTION SQL for the application hash bucket."""
    return (
        "CREATE OR REPLACE FUNCTION ctl.partition_bucket(key text) RETURNS text "
        "LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$ "
        f"{partition_bucket_sql()} "
        "$$;"
    )


def staging_table_sql(schema: str, table: str) -> str:
    """Return UNLOGGED staging table DDL copied from a canonical parent."""
    return (
        f"CREATE UNLOGGED TABLE IF NOT EXISTS {STAGING_SCHEMA}.{table} "
        f"(LIKE {schema}.{table} INCLUDING DEFAULTS INCLUDING COMMENTS)"
    )


def fact_check_sql() -> tuple[str, ...]:
    """Return CHECK constraints that enforce fact shape and provenance."""
    statuses = ", ".join(f"'{item}'" for item in FACT_STATUSES)
    return (
        "ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_subject_predicate "
        "CHECK (subject_object_id IS NOT NULL AND predicate_id IS NOT NULL)",
        "ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_object_xor_literal CHECK ("
        "(object_object_id IS NOT NULL AND literal_value IS NULL AND literal_type IS NULL) "
        "OR (object_object_id IS NULL AND literal_value IS NOT NULL AND literal_type IS NOT NULL)"
        ")",
        "ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_provenance "
        "CHECK (document_id IS NOT NULL AND extractor_id IS NOT NULL)",
        f"ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_status CHECK (status IN ({statuses}))",
    )


def embedding_profile_sql() -> tuple[str, ...]:
    """Return store-owned embedding profile table, trigger, and uniqueness."""
    schema, _, table = EMBEDDING_PROFILES_TABLE.partition(".")
    return (
        f"CREATE TABLE {EMBEDDING_PROFILES_TABLE} ("
        "profile_id TEXT PRIMARY KEY, "
        "dimensions BIGINT NOT NULL, "
        "model_digest TEXT NOT NULL, "
        "pooling TEXT, "
        "normalization TEXT, "
        "chunker_id TEXT, "
        "contract_version TEXT NOT NULL"
        ")",
        "CREATE OR REPLACE FUNCTION search.enforce_embedding_profile() "
        "RETURNS trigger LANGUAGE plpgsql AS $$ "
        "DECLARE profile RECORD; "
        "BEGIN "
        "IF NEW.profile_id IS NULL THEN RETURN NEW; END IF; "
        f"SELECT * INTO profile FROM {EMBEDDING_PROFILES_TABLE} "
        "WHERE profile_id = NEW.profile_id; "
        "IF NOT FOUND THEN "
        "RAISE EXCEPTION 'unknown embedding profile %', NEW.profile_id; "
        "END IF; "
        "IF NEW.dimensions IS DISTINCT FROM profile.dimensions THEN "
        "RAISE EXCEPTION 'embedding dimensions mix profile %', NEW.profile_id; "
        "END IF; "
        "IF NEW.model_digest IS DISTINCT FROM profile.model_digest THEN "
        "RAISE EXCEPTION 'embedding model digest mix profile %', NEW.profile_id; "
        "END IF; "
        "IF EXISTS ("
        "SELECT 1 FROM search.embeddings e WHERE e.embedding_id <> NEW.embedding_id "
        "AND e.target_kind IS NOT DISTINCT FROM NEW.target_kind "
        "AND e.target_id IS NOT DISTINCT FROM NEW.target_id "
        "AND e.profile_id IS NOT DISTINCT FROM NEW.profile_id"
        ") THEN "
        "RAISE EXCEPTION 'duplicate embedding target for profile %', NEW.profile_id; "
        "END IF; "
        "RETURN NEW; END; $$;",
        "DROP TRIGGER IF EXISTS trg_embeddings_profile ON search.embeddings",
        "CREATE TRIGGER trg_embeddings_profile BEFORE INSERT OR UPDATE ON search.embeddings "
        "FOR EACH ROW EXECUTE FUNCTION search.enforce_embedding_profile()",
        f"ALTER TABLE search.embeddings ADD CONSTRAINT fk_embeddings_profile "
        f"FOREIGN KEY (profile_id) REFERENCES {schema}.{table} (profile_id)",
    )


def correctness_index_sql() -> tuple[str, ...]:
    """Return indexes required for fact and evidence lookup, not corpus tuning."""
    return (
        "CREATE INDEX IF NOT EXISTS ix_facts_subject_object_id ON kg.facts (subject_object_id)",
        "CREATE INDEX IF NOT EXISTS ix_facts_status ON kg.facts (status)",
        "CREATE INDEX IF NOT EXISTS ix_facts_document_id ON kg.facts (document_id)",
        "CREATE INDEX IF NOT EXISTS ix_embeddings_profile_id ON search.embeddings (profile_id)",
    )


def grant_sql() -> tuple[str, ...]:
    """Return the role boundary: dbt writes derived only; pipeline writes canonical."""
    canonical = ", ".join(CANONICAL_SCHEMAS)
    statements = [
        f"GRANT {ROLE_MIGRATOR}, {ROLE_PIPELINE}, {ROLE_DBT}, {ROLE_READER} TO CURRENT_USER",
        f"GRANT USAGE ON SCHEMA {canonical} TO {ROLE_PIPELINE}, {ROLE_DBT}, {ROLE_READER}",
        f"GRANT USAGE, CREATE ON SCHEMA {STAGING_SCHEMA} TO {ROLE_PIPELINE}",
        f"GRANT USAGE ON SCHEMA {STAGING_SCHEMA} TO {ROLE_READER}",
        f"GRANT USAGE, CREATE ON SCHEMA {DERIVED_SCHEMA} TO {ROLE_DBT}",
        f"GRANT USAGE ON SCHEMA {DERIVED_SCHEMA} TO {ROLE_READER}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {canonical} "
        f"TO {ROLE_PIPELINE}",
        f"GRANT SELECT ON ALL TABLES IN SCHEMA {canonical} TO {ROLE_DBT}, {ROLE_READER}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA "
        f"{STAGING_SCHEMA} TO {ROLE_PIPELINE}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {canonical} GRANT SELECT, INSERT, UPDATE, "
        f"DELETE ON TABLES TO {ROLE_PIPELINE}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {canonical} GRANT SELECT ON TABLES "
        f"TO {ROLE_DBT}, {ROLE_READER}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {DERIVED_SCHEMA} GRANT SELECT ON TABLES "
        f"TO {ROLE_READER}",
        f"REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA {canonical} "
        f"FROM {ROLE_DBT}",
        "REVOKE ALL ON TABLE public.alembic_version FROM "
        f"{ROLE_DBT}, {ROLE_PIPELINE}, {ROLE_READER}",
        f"GRANT SELECT ON TABLE public.alembic_version TO {ROLE_READER}",
    ]
    return tuple(statements)


def owned_staging_sql() -> tuple[str, ...]:
    """Return staging table DDL for every owned canonical table."""
    return tuple(staging_table_sql(schema, table) for schema, table in OWNED_TABLES)

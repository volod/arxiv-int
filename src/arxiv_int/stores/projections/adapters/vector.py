"""pgvector candidate-index adapter for selected embedding rows."""

from sqlalchemy import Connection, text

from arxiv_int.stores.projections.ids import qualified_table, require_ident, table_name
from arxiv_int.stores.projections.model import ENGINE_PGVECTOR, KIND_VECTOR


def vector_table(version_id: str) -> str:
    """Return the versioned vector candidate table."""
    return qualified_table(KIND_VECTOR, version_id)


def vector_index(version_id: str) -> str:
    """Return the HNSW index name for one vector version."""
    return f"{table_name(KIND_VECTOR, version_id)}_hnsw"


def drop_vector(connection: Connection, version_id: str) -> None:
    """Drop a non-active vector table and index."""
    table = vector_table(version_id)
    connection.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))


def _dimensions(connection: Connection, source: str) -> int | None:
    schema, _, table = source.partition(".")
    require_ident(schema)
    require_ident(table)
    count = connection.execute(text(f"SELECT count(*) FROM {schema}.{table}")).scalar()
    if not count:
        return None
    value = connection.execute(
        text(f"SELECT MIN(dimensions) FROM {schema}.{table} WHERE dimensions IS NOT NULL")
    ).scalar()
    mixed = connection.execute(
        text(
            f"SELECT COUNT(DISTINCT dimensions) FROM {schema}.{table} WHERE dimensions IS NOT NULL"
        )
    ).scalar()
    if not value or int(mixed or 0) > 1:
        raise ValueError("vector projection requires one non-mixed embedding dimension")
    return int(value)


def build_vector(connection: Connection, version_id: str, source: str) -> str:
    """Materialize selected embeddings and create one pgvector HNSW candidate index."""
    target = vector_table(version_id)
    index_name = vector_index(version_id)
    schema, _, table = source.partition(".")
    require_ident(schema)
    require_ident(table)
    drop_vector(connection, version_id)
    dims = _dimensions(connection, source)
    if dims is None:
        connection.execute(
            text(
                f"CREATE TABLE {target} ("
                "embedding_id TEXT PRIMARY KEY, target_id TEXT, target_kind TEXT, "
                "profile_id TEXT, dimensions BIGINT, model_digest TEXT)"
            )
        )
        return target
    connection.execute(
        text(
            f"CREATE TABLE {target} ("
            "embedding_id TEXT PRIMARY KEY, "
            "target_id TEXT, "
            "target_kind TEXT, "
            "profile_id TEXT, "
            "dimensions BIGINT NOT NULL, "
            "model_digest TEXT, "
            f"embedding vector({dims}) NOT NULL"
            ")"
        )
    )
    connection.execute(
        text(
            f"INSERT INTO {target} ("
            "embedding_id, target_id, target_kind, profile_id, dimensions, "
            "model_digest, embedding) "
            f"SELECT embedding_id, target_id, target_kind, profile_id, dimensions, "
            f"model_digest, vector_ref::vector({dims}) FROM {schema}.{table} "
            "WHERE vector_ref IS NOT NULL AND dimensions IS NOT NULL"
        )
    )
    connection.execute(
        text(f"CREATE INDEX {index_name} ON {target} USING hnsw (embedding vector_l2_ops)")
    )
    return f"{target}:{index_name}"


def engine_name() -> str:
    """Return the vector engine identity."""
    return ENGINE_PGVECTOR

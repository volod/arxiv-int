"""ParadeDB BM25 covering-index adapter for lexical projection versions."""

from sqlalchemy import Connection, text

from arxiv_int.stores.projections.ids import qualified_table, require_ident, table_name
from arxiv_int.stores.projections.model import ENGINE_PARADEDB, KIND_LEXICAL

COVERING_COLUMNS = (
    "chunk_id",
    "document_id",
    "title",
    "body",
    "identifiers",
    "language",
)
TOKENIZER_PROFILE = (
    '{"body": {"tokenizer": {"type": "default", "stemmer": "Russian"}, '
    '"record": "position"}, '
    '"identifiers": {"tokenizer": {"type": "keyword"}}, '
    '"title": {"tokenizer": {"type": "default", "stemmer": "Russian"}}}'
)


def lexical_table(version_id: str) -> str:
    """Return the versioned lexical covering table."""
    return qualified_table(KIND_LEXICAL, version_id)


def lexical_index(version_id: str) -> str:
    """Return the BM25 index name for one lexical version."""
    return f"{table_name(KIND_LEXICAL, version_id)}_bm25"


def drop_lexical(connection: Connection, version_id: str) -> None:
    """Drop a non-active lexical table and index."""
    table = lexical_table(version_id)
    index_name = lexical_index(version_id)
    connection.execute(text(f"DROP INDEX IF EXISTS search.{require_ident(index_name)}"))
    connection.execute(text(f"DROP TABLE IF EXISTS {table}"))


def build_lexical(connection: Connection, version_id: str, source: str) -> str:
    """Materialize covering rows and create one ParadeDB BM25 index."""
    target = lexical_table(version_id)
    index_name = lexical_index(version_id)
    schema, _, table = source.partition(".")
    require_ident(schema)
    require_ident(table)
    drop_lexical(connection, version_id)
    columns = ", ".join(COVERING_COLUMNS)
    connection.execute(text(f"CREATE TABLE {target} AS SELECT {columns} FROM {schema}.{table}"))
    connection.execute(text(f"ALTER TABLE {target} ADD PRIMARY KEY (chunk_id)"))
    connection.execute(
        text(
            f"CREATE INDEX {index_name} ON {target} "
            "USING bm25 (chunk_id, body, identifiers, title, language) "
            f"WITH (key_field='chunk_id', text_fields='{TOKENIZER_PROFILE}')"
        )
    )
    return f"{target}:{index_name}"


def engine_name() -> str:
    """Return the lexical engine identity."""
    return ENGINE_PARADEDB

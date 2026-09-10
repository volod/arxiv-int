"""Named ParadeDB query assets for the lexical covering index.

Every ParadeDB search operator and query-builder call used by the retrieval path
lives here. Field names, tags, limits, and user text are bound parameters; only
whitelisted identifiers are ever composed into SQL text.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from arxiv_int.stores.projections.adapters.lexical import TEXT_FIELDS

SEARCH_FIELDS: tuple[str, ...] = ("body", "title")
FILTER_FIELDS: tuple[str, ...] = ("language", "document_id")
IDENTIFIER_FIELDS: tuple[str, ...] = ("identifiers", "document_id")
SNIPPET_FIELD = "body"
RESULT_COLUMNS: tuple[str, ...] = ("chunk_id", "document_id", "title", "language")


class LexicalFieldError(ValueError):
    """Raised when a requested search or filter field is not indexed."""


@dataclass(frozen=True, slots=True)
class BoundQuery:
    """One ParadeDB query expression and the parameters it binds."""

    expression: str
    parameters: dict[str, object] = field(default_factory=dict)


def require_fields(names: Sequence[str], allowed: Sequence[str]) -> tuple[str, ...]:
    """Return requested field names after checking them against the index."""
    unknown = [name for name in names if name not in allowed or name not in TEXT_FIELDS]
    if unknown:
        listed = ", ".join(sorted(unknown))
        known = ", ".join(allowed)
        raise LexicalFieldError(f"unindexed field(s) {listed}; indexed fields are {known}")
    return tuple(names)


def match_query(
    *,
    query_text: str,
    fields: Sequence[str] = SEARCH_FIELDS,
    filters: Mapping[str, str] | None = None,
    lenient: bool = False,
) -> BoundQuery:
    """Build a filtered multi-field BM25 query from bound parameters only."""
    selected = require_fields(fields, SEARCH_FIELDS)
    if not selected:
        raise LexicalFieldError("at least one search field is required")
    applied = {name: value for name, value in (filters or {}).items() if value}
    require_fields(tuple(applied), FILTER_FIELDS)
    parameters: dict[str, object] = {"query_text": query_text, "lenient": lenient}
    parsed = []
    for index, name in enumerate(selected):
        parameters[f"search_field_{index}"] = name
        parsed.append(
            f"paradedb.parse_with_field(:search_field_{index}, :query_text, lenient => :lenient)"
        )
    clauses = ["paradedb.boolean(should => ARRAY[" + ", ".join(parsed) + "])"]
    for index, (name, value) in enumerate(sorted(applied.items())):
        parameters[f"filter_field_{index}"] = name
        parameters[f"filter_value_{index}"] = value
        clauses.append(f"paradedb.term(:filter_field_{index}, :filter_value_{index})")
    return BoundQuery("paradedb.boolean(must => ARRAY[" + ", ".join(clauses) + "])", parameters)


def identifier_query(value: str) -> BoundQuery:
    """Build an exact literal lookup over the identifier and document fields."""
    parameters: dict[str, object] = {"identifier": value}
    terms = []
    for index, name in enumerate(IDENTIFIER_FIELDS):
        parameters[f"identifier_field_{index}"] = name
        terms.append(f"paradedb.term(:identifier_field_{index}, :identifier)")
    return BoundQuery("paradedb.boolean(should => ARRAY[" + ", ".join(terms) + "])", parameters)


def search_sql(table: str, query: BoundQuery, *, snippets: bool) -> str:
    """Return the ranked top-k statement, optionally with highlighted snippets."""
    columns = ", ".join(RESULT_COLUMNS)
    snippet = (
        f"paradedb.snippet({SNIPPET_FIELD}, start_tag => :start_tag, end_tag => :end_tag, "
        "max_num_chars => :snippet_chars)"
        if snippets
        else "NULL::text"
    )
    return (
        f"SELECT {columns}, paradedb.score(chunk_id) AS score, {snippet} AS snippet "
        f"FROM {table} WHERE chunk_id @@@ {query.expression} "
        "ORDER BY score DESC, chunk_id LIMIT :limit OFFSET :offset"
    )


def count_sql(table: str, query: BoundQuery) -> str:
    """Return the total-match statement for one query."""
    return f"SELECT count(*) FROM {table} WHERE chunk_id @@@ {query.expression}"


def facet_sql(table: str, query: BoundQuery, column: str) -> str:
    """Return grouped match counts for one whitelisted filter column."""
    require_fields((column,), FILTER_FIELDS)
    return (
        f"SELECT {column} AS value, count(*) AS matched "
        f"FROM {table} WHERE chunk_id @@@ {query.expression} "
        "GROUP BY 1 ORDER BY matched DESC, value LIMIT :facet_limit"
    )


def lookup_sql(table: str, query: BoundQuery) -> str:
    """Return the deterministic literal-identifier statement."""
    columns = ", ".join(RESULT_COLUMNS)
    return (
        f"SELECT {columns} FROM {table} WHERE chunk_id @@@ {query.expression} "
        "ORDER BY document_id, chunk_id LIMIT :limit"
    )


def explain_sql(statement: str) -> str:
    """Wrap one search statement in an analyzed textual plan."""
    return f"EXPLAIN (ANALYZE, VERBOSE, FORMAT TEXT) {statement}"


INDEX_SIZE_SQL = (
    "SELECT coalesce(pg_relation_size(to_regclass(:index_ref)), 0) AS index_bytes, "
    "coalesce(pg_total_relation_size(to_regclass(:table_ref)), 0) AS table_bytes"
)
BUILD_ACTIVITY_SQL = (
    "SELECT pid, state, wait_event_type, wait_event, "
    "extract(epoch FROM (now() - query_start)) AS elapsed_seconds "
    "FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() "
    "AND query ILIKE :pattern ORDER BY query_start, pid"
)

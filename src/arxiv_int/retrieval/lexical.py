"""Typed lexical search, filters, snippets, facets, and identifier lookup."""

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import Connection, CursorResult, text
from sqlalchemy.exc import SQLAlchemyError

from arxiv_int.retrieval.projection import (
    LexicalQueryError,
    LexicalTarget,
    active_target,
)
from arxiv_int.retrieval.query_normalization import (
    SELECTED_QUERY_PROFILE,
    query_policy_fingerprint,
    query_variants,
)
from arxiv_int.stores.projections.adapters.lexical_search import (
    FILTER_FIELDS,
    SEARCH_FIELDS,
    BoundQuery,
    LexicalFieldError,
    count_sql,
    explain_sql,
    facet_sql,
    identifier_query,
    lookup_sql,
    match_query,
    search_sql,
)

DEFAULT_LIMIT = 10
DEFAULT_SNIPPET_CHARS = 200
DEFAULT_FACET_LIMIT = 10
MAX_LIMIT = 1000
START_TAG = "[["
END_TAG = "]]"


@dataclass(frozen=True, slots=True)
class LexicalRequest:
    """One bounded lexical query with its filters and result shaping."""

    query: str
    limit: int = DEFAULT_LIMIT
    offset: int = 0
    fields: tuple[str, ...] = SEARCH_FIELDS
    language: str | None = None
    document_id: str | None = None
    snippets: bool = True
    snippet_chars: int = DEFAULT_SNIPPET_CHARS
    facets: tuple[str, ...] = ()
    facet_limit: int = DEFAULT_FACET_LIMIT
    lenient: bool = False
    query_profile: str = SELECTED_QUERY_PROFILE

    def __post_init__(self) -> None:
        if not self.query.strip():
            raise LexicalFieldError("a lexical query must contain at least one term")
        if not 0 < self.limit <= MAX_LIMIT:
            raise LexicalFieldError(f"limit must be between 1 and {MAX_LIMIT}")
        if self.offset < 0:
            raise LexicalFieldError("offset must not be negative")
        if self.snippet_chars <= 0:
            raise LexicalFieldError("snippet_chars must be positive")
        if not 0 < self.facet_limit <= MAX_LIMIT:
            raise LexicalFieldError(f"facet_limit must be between 1 and {MAX_LIMIT}")

    def filters(self) -> dict[str, str]:
        """Return the applied equality filters keyed by indexed field."""
        applied = {"language": self.language or "", "document_id": self.document_id or ""}
        return {name: value for name, value in applied.items() if value}


@dataclass(frozen=True, slots=True)
class LexicalHit:
    """One ranked chunk with the evidence needed to resolve its citation."""

    rank: int
    chunk_id: str
    document_id: str
    title: str
    language: str
    score: float
    snippet: str = ""

    def as_json_dict(self) -> dict[str, object]:
        """Return a secret-free result row."""
        return {
            "chunkId": self.chunk_id,
            "documentId": self.document_id,
            "language": self.language,
            "rank": self.rank,
            "score": self.score,
            "snippet": self.snippet,
            "title": self.title,
        }


@dataclass(frozen=True, slots=True)
class LexicalResult:
    """Ranked hits with total matches, facets, and the projection they came from."""

    target: LexicalTarget
    hits: tuple[LexicalHit, ...]
    total: int
    facets: Mapping[str, tuple[tuple[str, int], ...]] = field(default_factory=dict)
    elapsed_ms: float = 0.0
    query_profile: str = SELECTED_QUERY_PROFILE

    def as_json_dict(self) -> dict[str, object]:
        """Return a secret-free JSON view of one search."""
        return {
            "elapsedMs": self.elapsed_ms,
            "facets": {
                name: [{"matched": count, "value": value} for value, count in values]
                for name, values in sorted(self.facets.items())
            },
            "hits": [hit.as_json_dict() for hit in self.hits],
            "projection": self.target.as_json_dict(),
            "queryPolicyFingerprint": query_policy_fingerprint(),
            "queryProfile": self.query_profile,
            "total": self.total,
        }


def resolve_target(connection: Connection, target: LexicalTarget | None) -> LexicalTarget:
    """Return the supplied target or the active projection pointer."""
    return target if target is not None else active_target(connection)


def search(
    connection: Connection,
    request: LexicalRequest,
    *,
    target: LexicalTarget | None = None,
) -> LexicalResult:
    """Run one ranked BM25 query with filters, snippets, and optional facets."""
    resolved = resolve_target(connection, target)
    query = _query_for(request)
    started = time.perf_counter()
    rows = _execute(
        connection,
        search_sql(resolved.table, query, snippets=request.snippets),
        {**query.parameters, **_paging(request)},
    ).fetchall()
    total = int(
        _execute(connection, count_sql(resolved.table, query), query.parameters).scalar() or 0
    )
    facets = {
        name: _facet_counts(connection, resolved, query, name, request.facet_limit)
        for name in _facet_names(request)
    }
    elapsed = round((time.perf_counter() - started) * 1000, 3)
    hits = tuple(
        LexicalHit(
            rank=index,
            chunk_id=str(row.chunk_id),
            document_id=str(row.document_id or ""),
            title=str(row.title or ""),
            language=str(row.language or ""),
            score=float(row.score or 0.0),
            snippet=str(row.snippet or ""),
        )
        for index, row in enumerate(rows, request.offset + 1)
    )
    return LexicalResult(resolved, hits, total, facets, elapsed, request.query_profile)


def lookup(
    connection: Connection,
    identifier: str,
    *,
    limit: int = DEFAULT_LIMIT,
    target: LexicalTarget | None = None,
) -> tuple[LexicalHit, ...]:
    """Resolve one literal identifier against the exact identifier fields."""
    if not identifier.strip():
        raise LexicalFieldError("an identifier lookup needs a non-empty value")
    if not 0 < limit <= MAX_LIMIT:
        raise LexicalFieldError(f"limit must be between 1 and {MAX_LIMIT}")
    resolved = resolve_target(connection, target)
    query = identifier_query(identifier)
    rows = _execute(
        connection,
        lookup_sql(resolved.table, query),
        {**query.parameters, "limit": limit},
    ).fetchall()
    return tuple(
        LexicalHit(
            rank=index,
            chunk_id=str(row.chunk_id),
            document_id=str(row.document_id or ""),
            title=str(row.title or ""),
            language=str(row.language or ""),
            score=0.0,
        )
        for index, row in enumerate(rows, 1)
    )


def explain(
    connection: Connection,
    request: LexicalRequest,
    *,
    target: LexicalTarget | None = None,
) -> tuple[str, ...]:
    """Return the analyzed plan of one search, including the pushed-down query."""
    resolved = resolve_target(connection, target)
    query = _query_for(request)
    statement = search_sql(resolved.table, query, snippets=request.snippets)
    rows = _execute(
        connection,
        explain_sql(statement),
        {**query.parameters, **_paging(request)},
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _query_for(request: LexicalRequest) -> BoundQuery:
    variants = query_variants(request.query, profile_id=request.query_profile)
    return match_query(
        query_text=request.query,
        query_variants=variants[1:],
        fields=request.fields,
        filters=request.filters(),
        lenient=request.lenient,
    )


def _paging(request: LexicalRequest) -> dict[str, object]:
    return {
        "limit": request.limit,
        "offset": request.offset,
        "start_tag": START_TAG,
        "end_tag": END_TAG,
        "snippet_chars": request.snippet_chars,
    }


def _facet_names(request: LexicalRequest) -> Sequence[str]:
    if not request.facets:
        return ()
    unknown = [name for name in request.facets if name not in FILTER_FIELDS]
    if unknown:
        listed = ", ".join(sorted(unknown))
        raise LexicalFieldError(f"unfacetable field(s) {listed}; use {', '.join(FILTER_FIELDS)}")
    return request.facets


def _facet_counts(
    connection: Connection,
    target: LexicalTarget,
    query: BoundQuery,
    column: str,
    limit: int,
) -> tuple[tuple[str, int], ...]:
    rows = _execute(
        connection,
        facet_sql(target.table, query, column),
        {**query.parameters, "facet_limit": limit},
    ).fetchall()
    return tuple((str(row.value or ""), int(row.matched)) for row in rows)


def _execute(
    connection: Connection, statement: str, parameters: Mapping[str, object]
) -> CursorResult[Any]:
    try:
        return connection.execute(text(statement), dict(parameters))
    except SQLAlchemyError as error:
        raise LexicalQueryError(_query_detail(error)) from error


def _query_detail(error: SQLAlchemyError) -> str:
    message = str(getattr(error, "orig", None) or error).strip()
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    return "; ".join(lines[:2])[:400] if lines else error.__class__.__name__

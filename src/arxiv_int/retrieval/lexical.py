"""Typed lexical search, filters, snippets, facets, and identifier lookup."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Connection, Row

from arxiv_int.retrieval.lexical_model import (
    DEFAULT_FACET_LIMIT,
    DEFAULT_LIMIT,
    DEFAULT_SNIPPET_CHARS,
    MAX_LIMIT,
    LexicalHit,
    LexicalRequest,
    LexicalResult,
)
from arxiv_int.retrieval.lexical_stages import (
    STAGE_FALLBACK,
    STAGE_FUZZY,
    execute,
    match_stage,
    staged_search,
)
from arxiv_int.retrieval.projection import LexicalTarget, active_target
from arxiv_int.retrieval.query_normalization import query_plan
from arxiv_int.stores.projections.adapters.lexical_search import (
    FILTER_FIELDS,
    BoundQuery,
    LexicalFieldError,
    explain_sql,
    facet_sql,
    identifier_query,
    lookup_sql,
    search_sql,
)

__all__ = [
    "DEFAULT_FACET_LIMIT",
    "DEFAULT_LIMIT",
    "DEFAULT_SNIPPET_CHARS",
    "END_TAG",
    "MAX_LIMIT",
    "STAGE_FALLBACK",
    "STAGE_FUZZY",
    "START_TAG",
    "LexicalHit",
    "LexicalRequest",
    "LexicalResult",
    "explain",
    "lookup",
    "resolve_target",
    "search",
]

START_TAG = "[["
END_TAG = "]]"


def resolve_target(connection: Connection, target: LexicalTarget | None) -> LexicalTarget:
    """Return the supplied target or the active projection pointer."""
    return target if target is not None else active_target(connection)


def search(
    connection: Connection,
    request: LexicalRequest,
    *,
    target: LexicalTarget | None = None,
) -> LexicalResult:
    """Run one ranked BM25 query with filters, snippets, and optional facets.

    The profile's primary variants always run; its fallback and fuzzy stages run
    only when every earlier stage matched nothing.
    """
    resolved = resolve_target(connection, target)
    plan = query_plan(request.query, profile_id=request.query_profile)
    outcome = staged_search(connection, resolved, request, plan, _paging(request))
    facets = {
        name: _facet_counts(connection, resolved, outcome.query, name, request.facet_limit)
        for name in _facet_names(request)
    }
    hits = tuple(_hit(index, row) for index, row in enumerate(outcome.rows, request.offset + 1))
    return LexicalResult(
        resolved,
        hits,
        outcome.total,
        facets,
        outcome.elapsed_ms,
        request.query_profile,
        outcome.stage,
    )


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
    rows = execute(
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
    """Return the analyzed plan of the primary search stage, including the pushed-down query."""
    resolved = resolve_target(connection, target)
    plan = query_plan(request.query, profile_id=request.query_profile)
    query = match_stage(request, plan.primary)
    statement = search_sql(resolved.table, query, snippets=request.snippets)
    rows = execute(
        connection,
        explain_sql(statement),
        {**query.parameters, **_paging(request)},
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _hit(rank: int, row: Row[Any]) -> LexicalHit:
    return LexicalHit(
        rank=rank,
        chunk_id=str(row.chunk_id),
        document_id=str(row.document_id or ""),
        title=str(row.title or ""),
        language=str(row.language or ""),
        score=float(row.score or 0.0),
        snippet=str(row.snippet or ""),
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
    rows = execute(
        connection,
        facet_sql(target.table, query, column),
        {**query.parameters, "facet_limit": limit},
    ).fetchall()
    return tuple((str(row.value or ""), int(row.matched)) for row in rows)

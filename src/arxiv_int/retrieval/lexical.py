"""Typed lexical search, filters, snippets, facets, and identifier lookup."""

import time
from collections.abc import Mapping, Sequence
from typing import Any

from sqlalchemy import Connection, CursorResult, Row, text
from sqlalchemy.exc import SQLAlchemyError

from arxiv_int.retrieval.lexical_model import (
    DEFAULT_FACET_LIMIT,
    DEFAULT_LIMIT,
    DEFAULT_SNIPPET_CHARS,
    MAX_LIMIT,
    STAGE_PRIMARY,
    LexicalHit,
    LexicalRequest,
    LexicalResult,
)
from arxiv_int.retrieval.projection import (
    LexicalQueryError,
    LexicalTarget,
    active_target,
)
from arxiv_int.retrieval.query_normalization import QueryPlan, query_plan
from arxiv_int.stores.projections.adapters.lexical_search import (
    FILTER_FIELDS,
    BoundQuery,
    LexicalFieldError,
    count_sql,
    explain_sql,
    facet_sql,
    fuzzy_query,
    identifier_query,
    lookup_sql,
    match_query,
    search_sql,
)

__all__ = [
    "DEFAULT_FACET_LIMIT",
    "DEFAULT_LIMIT",
    "DEFAULT_SNIPPET_CHARS",
    "END_TAG",
    "MAX_LIMIT",
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
STAGE_FALLBACK = "fallback"
STAGE_FUZZY = "fuzzy"


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
    started = time.perf_counter()
    for current in _stages(request, plan):
        stage, query = current
        rows = _execute(
            connection,
            search_sql(resolved.table, query, snippets=request.snippets),
            {**query.parameters, **_paging(request)},
        ).fetchall()
        total = _total(connection, resolved, query, request, len(rows))
        if total:
            break
    facets = {
        name: _facet_counts(connection, resolved, query, name, request.facet_limit)
        for name in _facet_names(request)
    }
    elapsed = round((time.perf_counter() - started) * 1000, 3)
    hits = tuple(_hit(index, row) for index, row in enumerate(rows, request.offset + 1))
    return LexicalResult(resolved, hits, total, facets, elapsed, request.query_profile, stage)


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
    """Return the analyzed plan of the primary search stage, including the pushed-down query."""
    resolved = resolve_target(connection, target)
    plan = query_plan(request.query, profile_id=request.query_profile)
    query = _match(request, plan.primary)
    statement = search_sql(resolved.table, query, snippets=request.snippets)
    rows = _execute(
        connection,
        explain_sql(statement),
        {**query.parameters, **_paging(request)},
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _stages(request: LexicalRequest, plan: QueryPlan) -> list[tuple[str, BoundQuery]]:
    stages = [(STAGE_PRIMARY, _match(request, plan.primary))]
    if plan.fallback:
        stages.append((STAGE_FALLBACK, _match(request, plan.variants)))
    if plan.fuzzy:
        stages.append(
            (
                STAGE_FUZZY,
                fuzzy_query(
                    query_texts=plan.fuzzy, fields=request.fields, filters=request.filters()
                ),
            )
        )
    return stages


def _match(request: LexicalRequest, variants: Sequence[str]) -> BoundQuery:
    # variants[0] is the NFC-normalized base, so the primary clause is normalized too.
    return match_query(
        query_text=variants[0],
        query_variants=variants[1:],
        fields=request.fields,
        filters=request.filters(),
        lenient=request.lenient,
    )


def _total(
    connection: Connection,
    target: LexicalTarget,
    query: BoundQuery,
    request: LexicalRequest,
    returned: int,
) -> int:
    # A first page shorter than the limit already holds every match.
    if request.offset == 0 and returned < request.limit:
        return returned
    return int(_execute(connection, count_sql(target.table, query), query.parameters).scalar() or 0)


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

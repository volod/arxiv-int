"""Staged execution of one query plan against the active lexical projection.

The primary stage always runs. A later stage runs only when every earlier stage matched
nothing, and a stage the engine refuses does not hide a later one: the refusal is kept and
raised when no stage produces a match, so a genuinely broken query still reports its error.
"""

import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from sqlalchemy import Connection, CursorResult, Row, text
from sqlalchemy.exc import SQLAlchemyError

from arxiv_int.retrieval.lexical_model import STAGE_PRIMARY, LexicalRequest
from arxiv_int.retrieval.projection import LexicalQueryError, LexicalTarget
from arxiv_int.retrieval.query_normalization import QueryPlan
from arxiv_int.stores.projections.adapters.lexical_search import (
    BoundQuery,
    count_sql,
    fuzzy_query,
    match_query,
    search_sql,
)

STAGE_FALLBACK = "fallback"
STAGE_FUZZY = "fuzzy"


@dataclass(frozen=True, slots=True)
class StagedSearch:
    """The stage that produced the returned rows, plus the query used for facets."""

    stage: str
    query: BoundQuery
    rows: Sequence[Row[Any]]
    total: int
    elapsed_ms: float


def match_stage(request: LexicalRequest, variants: Sequence[str]) -> BoundQuery:
    """Bind one multi-field BM25 clause over every variant of one stage."""
    # variants[0] is the NFC-normalized base, so the primary clause is normalized too.
    return match_query(
        query_text=variants[0],
        query_variants=variants[1:],
        fields=request.fields,
        filters=request.filters(),
        lenient=request.lenient,
    )


def plan_stages(request: LexicalRequest, plan: QueryPlan) -> list[tuple[str, BoundQuery]]:
    """Return the ordered stages one plan may run."""
    stages = [(STAGE_PRIMARY, match_stage(request, plan.primary))]
    if plan.fallback:
        # A base the syntax guard held verbatim cannot be parsed, so scoring it again beside
        # its readable variants would refuse the whole clause.
        union = plan.fallback if plan.literal_primary else plan.variants
        stages.append((STAGE_FALLBACK, match_stage(request, union)))
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


def staged_search(
    connection: Connection,
    target: LexicalTarget,
    request: LexicalRequest,
    plan: QueryPlan,
    paging: Mapping[str, object],
) -> StagedSearch:
    """Run each stage until one matches, and report the stage that did."""
    started = time.perf_counter()
    refused: LexicalQueryError | None = None
    outcome = StagedSearch(STAGE_PRIMARY, BoundQuery(""), (), 0, 0.0)
    for stage, query in plan_stages(request, plan):
        outcome = StagedSearch(stage, query, (), 0, 0.0)
        try:
            rows = execute(
                connection,
                search_sql(target.table, query, snippets=request.snippets),
                {**query.parameters, **paging},
            ).fetchall()
            total = _total(connection, target, query, request, len(rows))
        except LexicalQueryError as error:
            refused = refused or error
            continue
        outcome = StagedSearch(stage, query, rows, total, 0.0)
        if total:
            break
    if refused is not None and not outcome.total:
        raise refused
    elapsed = round((time.perf_counter() - started) * 1000, 3)
    return StagedSearch(outcome.stage, outcome.query, outcome.rows, outcome.total, elapsed)


def execute(
    connection: Connection, statement: str, parameters: Mapping[str, object]
) -> CursorResult[Any]:
    """Run one bound statement, reporting the engine's own refusal message."""
    try:
        return connection.execute(text(statement), dict(parameters))
    except SQLAlchemyError as error:
        raise LexicalQueryError(_query_detail(error)) from error


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
    return int(execute(connection, count_sql(target.table, query), query.parameters).scalar() or 0)


def _query_detail(error: SQLAlchemyError) -> str:
    """Return one short actionable line from an engine refusal."""
    message = str(getattr(error, "orig", None) or error).strip()
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    return "; ".join(lines[:2])[:400] if lines else error.__class__.__name__

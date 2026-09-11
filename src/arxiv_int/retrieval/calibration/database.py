"""Transactional ParadeDB profile builds and held-out query execution."""

import json
import time
from collections.abc import Mapping

from sqlalchemy import Connection, text

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.evaluation.scoring.accuracy import percentile
from arxiv_int.retrieval.calibration.config import profile_text_fields
from arxiv_int.retrieval.calibration.model import (
    CalibrationCase,
    CalibrationChunk,
    CalibrationConfig,
    CalibrationProfile,
    CaseReading,
    ProfileReading,
)
from arxiv_int.retrieval.lexical import LexicalRequest, lookup, search
from arxiv_int.retrieval.metrics import (
    RetrievalCase,
    RetrievedChunk,
    SourceSpan,
    evaluate_retrieval,
)
from arxiv_int.retrieval.projection import LexicalTarget, index_size
from arxiv_int.stores.projections.adapters.lexical import INDEXED_COLUMNS
from arxiv_int.stores.projections.ids import require_ident

_INSERT = """
INSERT INTO {table} (chunk_id, document_id, title, body, identifiers, language)
VALUES (:chunk_id, :document_id, :title, :body, :identifiers, :language)
"""


def paradedb_version(connection: Connection) -> str:
    """Return the live extension version bound to the calibration evidence."""
    version = connection.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'pg_search'")
    ).scalar()
    if not version:
        raise ValueError("pg_search extension is not installed in the selected database")
    return str(version)


def evaluate_profiles(
    connection: Connection,
    config: CalibrationConfig,
    *,
    run_token: str,
) -> tuple[ProfileReading, ...]:
    """Build and score every profile on identical rows in the current transaction."""
    readings = []
    for index, profile in enumerate(config.profiles):
        table_name = require_ident(f"lexical_cal_{run_token}_{index}")
        index_name = require_ident(f"lexical_cal_{run_token}_{index}_bm25")
        table = f"search.{table_name}"
        _create_table(connection, table, config.corpus)
        tokenizer = profile_text_fields(profile)
        build_seconds = _create_index(connection, table, index_name, tokenizer)
        fingerprint = sha256_text(json.dumps(tokenizer, ensure_ascii=True, sort_keys=True))
        target = LexicalTarget(
            projection_id=f"calibration:{profile.profile_id}",
            version_id=run_token,
            table=table,
            index=index_name,
            row_count=len(config.corpus),
            checksum=config.fingerprint,
            status="calibration",
            tokenizer_fingerprint=fingerprint,
        )
        readings.append(
            _evaluate_profile(
                connection,
                config,
                profile,
                target,
                build_seconds=build_seconds,
                tokenizer_fingerprint=fingerprint,
            )
        )
    return tuple(readings)


def _create_table(connection: Connection, table: str, corpus: tuple[CalibrationChunk, ...]) -> None:
    connection.execute(
        text(
            f"CREATE TABLE {table} ("
            "chunk_id text PRIMARY KEY, document_id text NOT NULL, title text NOT NULL, "
            "body text NOT NULL, identifiers text NOT NULL, language text NOT NULL)"
        )
    )
    connection.execute(
        text(_INSERT.format(table=table)),
        [
            {
                "body": item.body,
                "chunk_id": item.chunk_id,
                "document_id": item.document_id,
                "identifiers": item.identifiers,
                "language": item.language,
                "title": item.title,
            }
            for item in corpus
        ],
    )


def _create_index(
    connection: Connection,
    table: str,
    index_name: str,
    tokenizer: Mapping[str, object],
) -> float:
    profile = json.dumps(tokenizer, ensure_ascii=True, sort_keys=True).replace("'", "''")
    columns = ", ".join(INDEXED_COLUMNS)
    started = time.perf_counter()
    connection.execute(
        text(
            f"CREATE INDEX {index_name} ON {table} USING bm25 ({columns}) "
            f"WITH (key_field='chunk_id', text_fields='{profile}')"
        )
    )
    return round(time.perf_counter() - started, 6)


def _evaluate_profile(
    connection: Connection,
    config: CalibrationConfig,
    profile: CalibrationProfile,
    target: LexicalTarget,
    *,
    build_seconds: float,
    tokenizer_fingerprint: str,
) -> ProfileReading:
    chunks = {item.chunk_id: item for item in config.corpus}
    readings = tuple(
        _score_case(connection, case, profile, target, chunks, k=config.k)
        for case in config.queries
    )
    retrieval_cases = tuple(
        _retrieval_case(case, reading.hit_ids, chunks)
        for case, reading in zip(config.queries, readings, strict=True)
    )
    metrics = evaluate_retrieval(retrieval_cases, k=config.k)
    sizes = index_size(connection, target)
    return ProfileReading(
        profile=profile,
        tokenizer_fingerprint=tokenizer_fingerprint,
        build_seconds=build_seconds,
        index_bytes=sizes["index_bytes"],
        table_bytes=sizes["table_bytes"],
        p95_latency_ms=round(percentile([item.elapsed_ms for item in readings]), 3),
        metrics=metrics,
        cases=readings,
    )


def _score_case(
    connection: Connection,
    case: CalibrationCase,
    profile: CalibrationProfile,
    target: LexicalTarget,
    chunks: Mapping[str, CalibrationChunk],
    *,
    k: int,
) -> CaseReading:
    hit_ids, elapsed = _execute_case(connection, case, profile, target, k=k)
    retrieval = _retrieval_case(case, hit_ids, chunks)
    metrics = evaluate_retrieval((retrieval,), k=k)
    return CaseReading(
        profile_id=profile.profile_id,
        case_id=case.case_id,
        category=case.category,
        split=case.split,
        hit_ids=hit_ids,
        recall=metrics.recall_at_k,
        reciprocal_rank=metrics.mean_reciprocal_rank,
        intact=metrics.span_intact_at_k,
        elapsed_ms=elapsed,
    )


def _execute_case(
    connection: Connection,
    case: CalibrationCase,
    profile: CalibrationProfile,
    target: LexicalTarget,
    *,
    k: int,
) -> tuple[tuple[str, ...], float]:
    if case.mode == "identifier":
        lookup(connection, case.query, limit=k, target=target)
        started = time.perf_counter()
        hits = lookup(connection, case.query, limit=k, target=target)
        elapsed = (time.perf_counter() - started) * 1000
    else:
        request = LexicalRequest(
            query=case.query,
            limit=k,
            snippets=False,
            query_profile=profile.query_profile,
        )
        search(connection, request, target=target)
        result = search(connection, request, target=target)
        hits, elapsed = result.hits, result.elapsed_ms
    return tuple(item.chunk_id for item in hits), round(elapsed, 3)


def _retrieval_case(
    case: CalibrationCase,
    hit_ids: tuple[str, ...],
    chunks: Mapping[str, CalibrationChunk],
) -> RetrievalCase:
    retrieved = tuple(
        RetrievedChunk(item.document_id, 0, len(item.body), item.body)
        for chunk_id in hit_ids
        if (item := chunks.get(chunk_id)) is not None
    )
    spans = tuple(
        SourceSpan(item.document_id, 0, len(item.body))
        for chunk_id in case.relevant_chunk_ids
        if (item := chunks.get(chunk_id)) is not None
    )
    return RetrievalCase(retrieved, spans)

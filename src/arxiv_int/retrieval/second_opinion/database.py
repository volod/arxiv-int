"""Transactional ParadeDB builds and repeated, order-randomized second-opinion queries."""

import json
import logging
import time
from collections.abc import Iterable, Mapping, Sequence
from itertools import islice
from random import Random

from sqlalchemy import Connection, text

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.retrieval.lexical import LexicalRequest, lookup, search
from arxiv_int.retrieval.projection import LexicalQueryError, LexicalTarget, index_size
from arxiv_int.retrieval.second_opinion.model import (
    MODE_IDENTIFIER,
    Arm,
    BuildReading,
    CaseRun,
    SplitCase,
)
from arxiv_int.retrieval.second_opinion.protocol import index_text_fields
from arxiv_int.stores.projections.adapters.lexical import INDEXED_COLUMNS
from arxiv_int.stores.projections.adapters.lexical_search import LexicalFieldError
from arxiv_int.stores.projections.ids import require_ident

_LOG = logging.getLogger(__name__)
ROW_COLUMNS = ("chunk_id", "document_id", "title", "body", "identifiers", "language")
INSERT_BATCH = 5000
STAGE_IDENTIFIER = "identifier"
STAGE_ERROR = "error"
ERROR_CHARS = 200
ORDER_STRIDE = 1_000_003
Observation = tuple[tuple[str, ...], str, str, float]


def paradedb_version(connection: Connection) -> str:
    """Return the live extension version bound to the evidence."""
    version = connection.execute(
        text("SELECT extversion FROM pg_extension WHERE extname = 'pg_search'")
    ).scalar()
    if not version:
        raise ValueError("pg_search extension is not installed in the selected database")
    return str(version)


def load_base(
    connection: Connection, token: str, rows: Iterable[Mapping[str, object]]
) -> tuple[str, int]:
    """Create the shared covering rows every profile table copies, in bounded batches."""
    table = f"search.{require_ident(f'so_{token}_base')}"
    connection.execute(
        text(
            f"CREATE TABLE {table} (chunk_id text PRIMARY KEY, document_id text NOT NULL, "
            "title text NOT NULL, body text NOT NULL, identifiers text NOT NULL, "
            "language text NOT NULL)"
        )
    )
    columns = ", ".join(ROW_COLUMNS)
    arrays = ", ".join(f"CAST(:{name} AS text[])" for name in ROW_COLUMNS)
    statement = text(f"INSERT INTO {table} ({columns}) SELECT * FROM unnest({arrays})")
    count = 0
    iterator = iter(rows)
    while batch := list(islice(iterator, INSERT_BATCH)):
        connection.execute(
            statement, {name: [str(row[name]) for row in batch] for name in ROW_COLUMNS}
        )
        count += len(batch)
    return table, count


def build_indexes(
    connection: Connection,
    base: str,
    profiles: Mapping[str, Mapping[str, object]],
    *,
    token: str,
    rows: int,
    repetitions: int,
    seed: int,
) -> tuple[dict[str, LexicalTarget], tuple[BuildReading, ...]]:
    """Copy identical rows per profile, then rebuild every index in seeded random orders."""
    if repetitions <= 0:
        raise ValueError("build repetitions must be positive")
    names = sorted(profiles)
    targets: dict[str, LexicalTarget] = {}
    declarations: dict[str, dict[str, object]] = {}
    for position, name in enumerate(names):
        table = f"search.{require_ident(f'so_{token}_{position}')}"
        connection.execute(text(f"CREATE TABLE {table} AS SELECT * FROM {base}"))
        connection.execute(text(f"ALTER TABLE {table} ADD PRIMARY KEY (chunk_id)"))
        declarations[name] = index_text_fields(profiles[name])
        targets[name] = LexicalTarget(
            projection_id=f"second-opinion:{name}",
            version_id=token,
            table=table,
            index=require_ident(f"so_{token}_{position}_bm25"),
            row_count=rows,
            checksum=token,
            status="calibration",
            tokenizer_fingerprint=tokenizer_fingerprint(declarations[name]),
        )
    samples: dict[str, list[float]] = {name: [] for name in names}
    for repetition in range(repetitions):
        order = list(names)
        Random(seed + repetition).shuffle(order)
        for name in order:
            target = targets[name]
            connection.execute(text(f"DROP INDEX IF EXISTS search.{target.index}"))
            samples[name].append(_create_index(connection, target, declarations[name]))
        _LOG.info("second-opinion build repetition %d/%d complete", repetition + 1, repetitions)
    readings = []
    for name in names:
        sizes = index_size(connection, targets[name])
        readings.append(
            BuildReading(
                index_profile=name,
                tokenizer_fingerprint=targets[name].tokenizer_fingerprint,
                build_seconds=tuple(samples[name]),
                index_bytes=sizes["index_bytes"],
                table_bytes=sizes["table_bytes"],
                rows=rows,
            )
        )
    return targets, tuple(readings)


def run_queries(
    connection: Connection,
    arms: Sequence[Arm],
    targets: Mapping[str, LexicalTarget],
    cases: Sequence[SplitCase],
    *,
    k: int,
    repetitions: int,
    warmup: int,
    seed: int,
) -> tuple[CaseRun, ...]:
    """Run every arm/case pair ``repetitions`` times in a fresh seeded order each time."""
    if repetitions <= 0:
        raise ValueError("query repetitions must be positive")
    pairs = [(arm, case) for arm in arms for case in cases]
    for _ in range(warmup):
        for arm, case in pairs:
            _observe(connection, arm, case, targets[arm.index_profile], k)
    observed: list[list[Observation]] = [[] for _ in pairs]
    for repetition in range(repetitions):
        order = list(range(len(pairs)))
        Random(seed * ORDER_STRIDE + repetition).shuffle(order)
        for position in order:
            arm, case = pairs[position]
            observed[position].append(
                _observe(connection, arm, case, targets[arm.index_profile], k)
            )
        _LOG.info("second-opinion query repetition %d/%d complete", repetition + 1, repetitions)
    return tuple(
        _case_run(arm, case, observed[position]) for position, (arm, case) in enumerate(pairs)
    )


def tokenizer_fingerprint(declaration: Mapping[str, object]) -> str:
    """Hash one text-fields declaration exactly as the production adapter does."""
    return sha256_text(json.dumps(declaration, ensure_ascii=True, sort_keys=True))


def _create_index(
    connection: Connection, target: LexicalTarget, declaration: Mapping[str, object]
) -> float:
    profile = json.dumps(declaration, ensure_ascii=True, sort_keys=True).replace("'", "''")
    started = time.perf_counter()
    connection.execute(
        text(
            f"CREATE INDEX {target.index} ON {target.table} USING bm25 "
            f"({', '.join(INDEXED_COLUMNS)}) WITH (key_field='chunk_id', text_fields='{profile}')"
        )
    )
    return round(time.perf_counter() - started, 6)


def _observe(
    connection: Connection, arm: Arm, case: SplitCase, target: LexicalTarget, k: int
) -> Observation:
    try:
        with connection.begin_nested():
            if case.mode == MODE_IDENTIFIER:
                started = time.perf_counter()
                found = lookup(connection, case.query, limit=k, target=target)
                elapsed = round((time.perf_counter() - started) * 1000, 3)
                return tuple(item.chunk_id for item in found), STAGE_IDENTIFIER, "", elapsed
            request = LexicalRequest(
                query=case.query, limit=k, snippets=False, query_profile=arm.query_profile
            )
            result = search(connection, request, target=target)
            return (
                tuple(item.chunk_id for item in result.hits),
                result.query_stage,
                "",
                result.elapsed_ms,
            )
    except (LexicalQueryError, LexicalFieldError) as error:
        return (), STAGE_ERROR, str(error)[:ERROR_CHARS], 0.0


def _case_run(arm: Arm, case: SplitCase, observed: Sequence[Observation]) -> CaseRun:
    hits, stage, error, _elapsed = observed[0]
    return CaseRun(
        arm_id=arm.arm_id,
        case_id=case.case_id,
        hits=hits,
        stage=stage,
        error=error,
        latencies_ms=tuple(item[3] for item in observed if not item[2]),
        stable=all(item[:3] == (hits, stage, error) for item in observed),
    )

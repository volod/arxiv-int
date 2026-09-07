"""Bound SQLAlchemy transactions against ctl run-ledger tables."""

from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import replace
from typing import TypeVar
from uuid import uuid4

from sqlalchemy import Engine, Table, and_, func, insert, select, update
from sqlalchemy.engine import Connection, RowMapping

from arxiv_int.pipeline.control.lineage import LineageEdge
from arxiv_int.pipeline.control.model import RunRecord, ShardRecord, StageRecord
from arxiv_int.pipeline.control.postgres_codec import (
    as_datetime,
    assigned_shard,
    insert_resource_lease,
    run_from_row,
    shard_from_row,
    shard_values,
    stage_from_row,
)
from arxiv_int.pipeline.control.postgres_events import PostgresEventMixin
from arxiv_int.pipeline.control.states import ShardStatus, require_transition
from arxiv_int.pipeline.control.tables import ARTIFACT_LINEAGE, RUNS, SHARD_RUNS, STAGE_RUNS

__all__ = ["PostgresControlLedger", "insert_resource_lease"]

_TRecord = TypeVar("_TRecord", RunRecord, StageRecord)


class PostgresControlLedger(PostgresEventMixin):
    """Control ledger persisted with bound SQLAlchemy transactions."""

    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _begin(self) -> AbstractContextManager[Connection]:
        return self._engine.begin()

    def ensure_run(
        self, run_id: str, generation_id: str, config_fingerprint: str, now: float
    ) -> RunRecord:
        stamp = as_datetime(now)
        with self._begin() as connection:
            existing = (
                connection.execute(select(RUNS).where(RUNS.c.run_id == run_id)).mappings().first()
            )
            if existing is not None:
                record = run_from_row(existing)
                if record.generation_id != generation_id:
                    raise ValueError(f"run {run_id} already has generation {record.generation_id}")
                if record.config_fingerprint != config_fingerprint:
                    raise ValueError(f"run {run_id} configuration is immutable")
                return record
            connection.execute(
                insert(RUNS).values(
                    run_id=run_id,
                    generation_id=generation_id,
                    status="pending",
                    config_fingerprint=config_fingerprint,
                    created_at=stamp,
                    updated_at=stamp,
                )
            )
        return RunRecord(run_id, generation_id, "pending", config_fingerprint, now, now)

    def transition_run(self, run_id: str, status: str, now: float) -> RunRecord:
        return self._transition(RUNS, "run_id", run_id, "run", status, now, run_from_row)

    def ensure_stage(self, run_id: str, stage: str, stage_version: str, now: float) -> StageRecord:
        stamp = as_datetime(now)
        with self._begin() as connection:
            existing = (
                connection.execute(
                    select(STAGE_RUNS).where(
                        and_(STAGE_RUNS.c.run_id == run_id, STAGE_RUNS.c.stage_name == stage)
                    )
                )
                .mappings()
                .first()
            )
            if existing is not None:
                record = stage_from_row(existing)
                if record.stage_version != stage_version:
                    raise ValueError(f"stage {stage} version is immutable for run {run_id}")
                return record
            stage_run_id = uuid4().hex
            connection.execute(
                insert(STAGE_RUNS).values(
                    stage_run_id=stage_run_id,
                    run_id=run_id,
                    stage_name=stage,
                    stage_version=stage_version,
                    status="pending",
                    created_at=stamp,
                    updated_at=stamp,
                )
            )
        return StageRecord(stage_run_id, run_id, stage, stage_version, "pending", now, now)

    def transition_stage(self, stage_run_id: str, status: str, now: float) -> StageRecord:
        return self._transition(
            STAGE_RUNS, "stage_run_id", stage_run_id, "stage", status, now, stage_from_row
        )

    def next_attempt(self, reuse_key: str) -> int:
        with self._engine.connect() as connection:
            highest = connection.execute(
                select(func.max(SHARD_RUNS.c.attempt)).where(SHARD_RUNS.c.reuse_key == reuse_key)
            ).scalar()
        return int(highest or 0) + 1

    def add_shard(self, record: ShardRecord) -> ShardRecord:
        with self._begin() as connection:
            assigned = assigned_shard(connection, record)
            connection.execute(insert(SHARD_RUNS).values(**shard_values(assigned)))
        return assigned

    def get_shard(self, shard_run_id: str) -> ShardRecord:
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    select(SHARD_RUNS).where(SHARD_RUNS.c.shard_run_id == shard_run_id)
                )
                .mappings()
                .one()
            )
        return shard_from_row(row)

    def reusable_shard(self, reuse_key: str) -> ShardRecord | None:
        with self._engine.connect() as connection:
            row = (
                connection.execute(
                    select(SHARD_RUNS)
                    .where(
                        and_(
                            SHARD_RUNS.c.reuse_key == reuse_key,
                            SHARD_RUNS.c.status.in_(("succeeded", "quarantined")),
                            SHARD_RUNS.c.directory.is_not(None),
                            SHARD_RUNS.c.cache_hit == "false",
                        )
                    )
                    .order_by(SHARD_RUNS.c.attempt.desc(), SHARD_RUNS.c.updated_at.desc())
                    .limit(1)
                )
                .mappings()
                .first()
            )
        return None if row is None else shard_from_row(row)

    def transition_shard(
        self,
        shard_run_id: str,
        status: ShardStatus,
        now: float,
        *,
        cache_hit: bool | None = None,
        directory: str | None = None,
        lease_id: str | None = None,
        quality_warnings: tuple[str, ...] | None = None,
    ) -> ShardRecord:
        with self._begin() as connection:
            current = shard_from_row(
                connection.execute(
                    select(SHARD_RUNS).where(SHARD_RUNS.c.shard_run_id == shard_run_id)
                )
                .mappings()
                .one()
            )
            require_transition("shard", current.status, status)
            updated = replace(
                current,
                status=status,
                updated_at=now,
                cache_hit=current.cache_hit if cache_hit is None else cache_hit,
                directory=current.directory if directory is None else directory,
                lease_id=current.lease_id if lease_id is None else lease_id,
                quality_warnings=(
                    current.quality_warnings if quality_warnings is None else quality_warnings
                ),
            )
            connection.execute(
                update(SHARD_RUNS)
                .where(SHARD_RUNS.c.shard_run_id == shard_run_id)
                .values(**shard_values(updated))
            )
        return updated

    def shards(self) -> tuple[ShardRecord, ...]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(SHARD_RUNS)).mappings().all()
        return tuple(shard_from_row(row) for row in rows)

    def lineage(self) -> tuple[LineageEdge, ...]:
        with self._engine.connect() as connection:
            rows = connection.execute(select(ARTIFACT_LINEAGE)).mappings().all()
        return tuple(
            LineageEdge(str(row["producer_reuse_key"]), str(row["consumer_reuse_key"]))
            for row in rows
        )

    def mark_stale(self, reuse_keys: frozenset[str], now: float) -> tuple[str, ...]:
        changed: list[str] = []
        with self._begin() as connection:
            rows = connection.execute(select(SHARD_RUNS)).mappings().all()
            for row in rows:
                record = shard_from_row(row)
                if record.reuse_key not in reuse_keys:
                    continue
                if record.status in {"stale", "pruned", "superseded"}:
                    continue
                require_transition("shard", record.status, "stale")
                connection.execute(
                    update(SHARD_RUNS)
                    .where(SHARD_RUNS.c.shard_run_id == record.shard_run_id)
                    .values(status="stale", updated_at=as_datetime(now))
                )
                changed.append(record.reuse_key)
        return tuple(sorted(set(changed)))

    def _transition(
        self,
        table: Table,
        key: str,
        identity: str,
        kind: str,
        status: str,
        now: float,
        loader: Callable[[RowMapping], _TRecord],
    ) -> _TRecord:
        column = table.c[key]
        with self._begin() as connection:
            row = connection.execute(select(table).where(column == identity)).mappings().one()
            current = loader(row)
            require_transition(kind, str(current.status), status)
            connection.execute(
                update(table)
                .where(column == identity)
                .values(status=status, updated_at=as_datetime(now))
            )
        return replace(current, status=status, updated_at=now)

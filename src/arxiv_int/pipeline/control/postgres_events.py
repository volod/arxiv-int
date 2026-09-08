"""Lease, checkpoint, error, manifest, and lineage writes for the SQL ledger."""

from contextlib import AbstractContextManager
from dataclasses import replace
from uuid import uuid4

from sqlalchemy import Engine, and_, insert, select, update
from sqlalchemy.engine import Connection

from arxiv_int.pipeline.control.lineage import LineageEdge
from arxiv_int.pipeline.control.model import (
    CheckpointRecord,
    ErrorRecord,
    LeaseRecord,
    ManifestRecord,
)
from arxiv_int.pipeline.control.postgres_codec import as_datetime, lease_from_row, lock_reuse_key
from arxiv_int.pipeline.control.states import (
    FailureClass,
    ManifestStatus,
    as_lease_status,
    require_transition,
)
from arxiv_int.pipeline.control.store import LeaseExpiredError, LeaseHeldError
from arxiv_int.pipeline.control.tables import (
    ARTIFACT_LINEAGE,
    ARTIFACT_MANIFESTS,
    CHECKPOINTS,
    REUSE_LEASES,
    SHARD_ERRORS,
)


class PostgresEventMixin:
    """Event and lease methods mixed into ``PostgresControlLedger``."""

    _engine: Engine

    def _begin(self) -> AbstractContextManager[Connection]:
        raise NotImplementedError

    def acquire_lease(
        self,
        reuse_key: str,
        holder_shard_run_id: str,
        now: float,
        ttl_seconds: float,
    ) -> LeaseRecord:
        stamp = as_datetime(now)
        expires = as_datetime(now + ttl_seconds)
        with self._begin() as connection:
            lock_reuse_key(connection, reuse_key)
            rows = (
                connection.execute(
                    select(REUSE_LEASES)
                    .where(REUSE_LEASES.c.reuse_key == reuse_key)
                    .with_for_update()
                )
                .mappings()
                .all()
            )
            for row in rows:
                record = lease_from_row(row)
                if record.status != "acquired":
                    continue
                if record.expires_at <= now:
                    connection.execute(
                        update(REUSE_LEASES)
                        .where(REUSE_LEASES.c.lease_id == record.lease_id)
                        .values(status="expired", heartbeat_at=stamp)
                    )
                    continue
                if record.holder_shard_run_id != holder_shard_run_id:
                    raise LeaseHeldError(record)
                connection.execute(
                    update(REUSE_LEASES)
                    .where(REUSE_LEASES.c.lease_id == record.lease_id)
                    .values(heartbeat_at=stamp, expires_at=expires)
                )
                return replace(record, heartbeat_at=now, expires_at=now + ttl_seconds)
            lease_id = uuid4().hex
            connection.execute(
                insert(REUSE_LEASES).values(
                    lease_id=lease_id,
                    reuse_key=reuse_key,
                    holder_shard_run_id=holder_shard_run_id,
                    status="acquired",
                    acquired_at=stamp,
                    heartbeat_at=stamp,
                    expires_at=expires,
                )
            )
        return LeaseRecord(
            lease_id, reuse_key, holder_shard_run_id, "acquired", now, now, now + ttl_seconds
        )

    def heartbeat_lease(self, lease_id: str, now: float, ttl_seconds: float) -> LeaseRecord:
        with self._begin() as connection:
            current = lease_from_row(
                connection.execute(
                    select(REUSE_LEASES)
                    .where(REUSE_LEASES.c.lease_id == lease_id)
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            if current.status != "acquired" or current.expires_at <= now:
                raise LeaseExpiredError("publication lease expired")
            require_transition("lease", current.status, "acquired")
            connection.execute(
                update(REUSE_LEASES)
                .where(REUSE_LEASES.c.lease_id == lease_id)
                .values(heartbeat_at=as_datetime(now), expires_at=as_datetime(now + ttl_seconds))
            )
        return replace(current, heartbeat_at=now, expires_at=now + ttl_seconds)

    def release_lease(self, lease_id: str, now: float, status: str = "released") -> LeaseRecord:
        with self._begin() as connection:
            current = lease_from_row(
                connection.execute(
                    select(REUSE_LEASES)
                    .where(REUSE_LEASES.c.lease_id == lease_id)
                    .with_for_update()
                )
                .mappings()
                .one()
            )
            target = as_lease_status(status)
            require_transition("lease", current.status, target)
            connection.execute(
                update(REUSE_LEASES)
                .where(REUSE_LEASES.c.lease_id == lease_id)
                .values(status=target, heartbeat_at=as_datetime(now))
            )
        return replace(current, status=target, heartbeat_at=now)

    def add_checkpoint(
        self, shard_run_id: str, sequence: int, payload_digest: str, now: float
    ) -> CheckpointRecord:
        record = CheckpointRecord(uuid4().hex, shard_run_id, sequence, payload_digest, now)
        with self._begin() as connection:
            connection.execute(
                insert(CHECKPOINTS).values(
                    checkpoint_id=record.checkpoint_id,
                    shard_run_id=shard_run_id,
                    sequence=sequence,
                    payload_digest=payload_digest,
                    created_at=as_datetime(now),
                )
            )
        return record

    def add_error(
        self,
        shard_run_id: str,
        attempt: int,
        code: str,
        failure_class: FailureClass,
        detail: str,
        now: float,
    ) -> ErrorRecord:
        record = ErrorRecord(uuid4().hex, shard_run_id, attempt, code, failure_class, detail, now)
        with self._begin() as connection:
            connection.execute(
                insert(SHARD_ERRORS).values(
                    error_id=record.error_id,
                    shard_run_id=shard_run_id,
                    attempt=attempt,
                    code=code,
                    failure_class=failure_class,
                    detail=detail,
                    created_at=as_datetime(now),
                )
            )
        return record

    def add_manifest(
        self,
        shard_run_id: str,
        attempt: int,
        reuse_key: str,
        relative_path: str,
        status: ManifestStatus,
        sha256: str,
        byte_count: int,
        now: float,
    ) -> ManifestRecord:
        require_transition("manifest", "staging", status)
        record = ManifestRecord(
            uuid4().hex,
            shard_run_id,
            attempt,
            reuse_key,
            relative_path,
            status,
            sha256,
            byte_count,
            now,
        )
        with self._begin() as connection:
            connection.execute(
                insert(ARTIFACT_MANIFESTS).values(
                    manifest_id=record.manifest_id,
                    shard_run_id=shard_run_id,
                    attempt=attempt,
                    reuse_key=reuse_key,
                    relative_path=relative_path,
                    status=status,
                    sha256=sha256,
                    byte_count=byte_count,
                    created_at=as_datetime(now),
                )
            )
        return record

    def add_lineage(self, producer_reuse_key: str, consumer_reuse_key: str) -> LineageEdge:
        edge = LineageEdge(producer_reuse_key, consumer_reuse_key)
        with self._begin() as connection:
            existing = connection.execute(
                select(ARTIFACT_LINEAGE.c.edge_id).where(
                    and_(
                        ARTIFACT_LINEAGE.c.producer_reuse_key == producer_reuse_key,
                        ARTIFACT_LINEAGE.c.consumer_reuse_key == consumer_reuse_key,
                    )
                )
            ).first()
            if existing is None:
                connection.execute(
                    insert(ARTIFACT_LINEAGE).values(
                        edge_id=uuid4().hex,
                        producer_reuse_key=producer_reuse_key,
                        consumer_reuse_key=consumer_reuse_key,
                    )
                )
        return edge

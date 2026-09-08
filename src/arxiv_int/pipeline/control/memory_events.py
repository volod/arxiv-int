"""Lease, checkpoint, error, manifest, and lineage maps for the in-memory ledger."""

from dataclasses import replace
from uuid import uuid4

from arxiv_int.interfaces.tokens import require_token
from arxiv_int.pipeline.control.lineage import LineageEdge
from arxiv_int.pipeline.control.model import (
    CheckpointRecord,
    ErrorRecord,
    LeaseRecord,
    ManifestRecord,
    ShardRecord,
)
from arxiv_int.pipeline.control.states import (
    FailureClass,
    ManifestStatus,
    as_lease_status,
    require_transition,
)
from arxiv_int.pipeline.control.store import LeaseExpiredError, LeaseHeldError


class InMemoryEventMixin:
    """Event methods mixed into ``InMemoryLedger``."""

    _checkpoints: dict[str, CheckpointRecord]
    _edges: list[LineageEdge]
    _errors: dict[str, ErrorRecord]
    _leases: dict[str, LeaseRecord]
    _manifests: dict[str, ManifestRecord]
    _shards: dict[str, ShardRecord]

    def acquire_lease(
        self,
        reuse_key: str,
        holder_shard_run_id: str,
        now: float,
        ttl_seconds: float,
    ) -> LeaseRecord:
        require_token(reuse_key, "reuse_key")
        require_token(holder_shard_run_id, "holder_shard_run_id")
        active = self._active_lease(reuse_key, now)
        if active is not None:
            if active.holder_shard_run_id != holder_shard_run_id:
                raise LeaseHeldError(active)
            return self.heartbeat_lease(active.lease_id, now, ttl_seconds)
        record = LeaseRecord(
            uuid4().hex, reuse_key, holder_shard_run_id, "acquired", now, now, now + ttl_seconds
        )
        self._leases[record.lease_id] = record
        return record

    def heartbeat_lease(self, lease_id: str, now: float, ttl_seconds: float) -> LeaseRecord:
        current = self._leases[lease_id]
        if current.status != "acquired" or current.expires_at <= now:
            raise LeaseExpiredError("publication lease expired")
        require_transition("lease", current.status, "acquired")
        updated = replace(current, heartbeat_at=now, expires_at=now + ttl_seconds)
        self._leases[lease_id] = updated
        return updated

    def release_lease(self, lease_id: str, now: float, status: str = "released") -> LeaseRecord:
        current = self._leases[lease_id]
        target = as_lease_status(status)
        require_transition("lease", current.status, target)
        updated = replace(current, status=target, heartbeat_at=now)
        self._leases[lease_id] = updated
        return updated

    def add_checkpoint(
        self, shard_run_id: str, sequence: int, payload_digest: str, now: float
    ) -> CheckpointRecord:
        require_token(payload_digest, "payload_digest")
        record = CheckpointRecord(uuid4().hex, shard_run_id, sequence, payload_digest, now)
        self._checkpoints[record.checkpoint_id] = record
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
        self._errors[record.error_id] = record
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
        self._manifests[record.manifest_id] = record
        return record

    def add_lineage(self, producer_reuse_key: str, consumer_reuse_key: str) -> LineageEdge:
        edge = LineageEdge(producer_reuse_key, consumer_reuse_key)
        if edge not in self._edges:
            self._edges.append(edge)
        return edge

    def lineage(self) -> tuple[LineageEdge, ...]:
        return tuple(self._edges)

    def mark_stale(self, reuse_keys: frozenset[str], now: float) -> tuple[str, ...]:
        changed: list[str] = []
        for record in list(self._shards.values()):
            if record.reuse_key not in reuse_keys or record.status in {
                "stale",
                "pruned",
                "superseded",
            }:
                continue
            require_transition("shard", record.status, "stale")
            self._shards[record.shard_run_id] = replace(record, status="stale", updated_at=now)
            changed.append(record.reuse_key)
        return tuple(sorted(set(changed)))

    def _active_lease(self, reuse_key: str, now: float) -> LeaseRecord | None:
        for record in self._leases.values():
            if record.reuse_key != reuse_key or record.status != "acquired":
                continue
            if record.expires_at <= now:
                self.release_lease(record.lease_id, now, status="expired")
                continue
            return record
        return None

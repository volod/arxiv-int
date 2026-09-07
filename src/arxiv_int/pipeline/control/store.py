"""Ledger protocol for inspectable run, shard, lease, and lineage state."""

from typing import Protocol

from arxiv_int.pipeline.control.lineage import LineageEdge
from arxiv_int.pipeline.control.model import (
    CheckpointRecord,
    ErrorRecord,
    LeaseRecord,
    ManifestRecord,
    RunRecord,
    ShardRecord,
    StageRecord,
)
from arxiv_int.pipeline.control.states import FailureClass, ManifestStatus, ShardStatus


class LeaseHeldError(RuntimeError):
    """Another worker holds an unexpired lease for the same reuse key."""

    def __init__(self, lease: LeaseRecord) -> None:
        super().__init__(f"reuse key is leased by {lease.holder_shard_run_id}")
        self.lease = lease


class ControlLedger(Protocol):
    """Persist control-plane rows behind bound transactions or an in-memory map."""

    def ensure_run(
        self, run_id: str, generation_id: str, config_fingerprint: str, now: float
    ) -> RunRecord:
        """Create or return the immutable run configuration."""

    def transition_run(self, run_id: str, status: str, now: float) -> RunRecord:
        """Move a run to a legal status."""

    def ensure_stage(
        self,
        run_id: str,
        stage: str,
        stage_version: str,
        now: float,
    ) -> StageRecord:
        """Create or return the stage row for this run."""

    def transition_stage(self, stage_run_id: str, status: str, now: float) -> StageRecord:
        """Move a stage to a legal status."""

    def next_attempt(self, reuse_key: str) -> int:
        """Return the next attempt number for a reuse key."""

    def add_shard(self, record: ShardRecord) -> ShardRecord:
        """Insert one shard attempt."""

    def get_shard(self, shard_run_id: str) -> ShardRecord:
        """Return one shard attempt."""

    def reusable_shard(self, reuse_key: str) -> ShardRecord | None:
        """Return the latest succeeded, non-stale shard for a reuse key."""

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
        """Move a shard to a legal status and optionally record publication."""

    def shards(self) -> tuple[ShardRecord, ...]:
        """Return every shard attempt."""

    def acquire_lease(
        self,
        reuse_key: str,
        holder_shard_run_id: str,
        now: float,
        ttl_seconds: float,
    ) -> LeaseRecord:
        """Take or recover the exclusive lease for a reuse key."""

    def heartbeat_lease(self, lease_id: str, now: float, ttl_seconds: float) -> LeaseRecord:
        """Refresh an acquired lease."""

    def release_lease(self, lease_id: str, now: float, status: str = "released") -> LeaseRecord:
        """Release, fail, or expire a lease."""

    def add_checkpoint(
        self, shard_run_id: str, sequence: int, payload_digest: str, now: float
    ) -> CheckpointRecord:
        """Record a restartable checkpoint."""

    def add_error(
        self,
        shard_run_id: str,
        attempt: int,
        code: str,
        failure_class: FailureClass,
        detail: str,
        now: float,
    ) -> ErrorRecord:
        """Append classified error evidence."""

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
        """Record one artifact-manifest pointer."""

    def add_lineage(self, producer_reuse_key: str, consumer_reuse_key: str) -> LineageEdge:
        """Record a transitive producer-to-consumer edge."""

    def lineage(self) -> tuple[LineageEdge, ...]:
        """Return every recorded lineage edge."""

    def mark_stale(self, reuse_keys: frozenset[str], now: float) -> tuple[str, ...]:
        """Mark the selected succeeded/quarantined shards stale."""

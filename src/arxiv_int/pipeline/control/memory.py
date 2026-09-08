"""In-memory control ledger used by network-free tests and fixture runners."""

from dataclasses import replace
from uuid import uuid4

from arxiv_int.interfaces.tokens import require_token
from arxiv_int.pipeline.control.lineage import LineageEdge
from arxiv_int.pipeline.control.memory_events import InMemoryEventMixin
from arxiv_int.pipeline.control.model import (
    CheckpointRecord,
    ErrorRecord,
    LeaseRecord,
    ManifestRecord,
    RunRecord,
    ShardRecord,
    StageRecord,
)
from arxiv_int.pipeline.control.states import ShardStatus, require_transition


class InMemoryLedger(InMemoryEventMixin):
    """Process-local maps with the same transition rules as the SQL ledger."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}
        self._stages: dict[str, StageRecord] = {}
        self._shards: dict[str, ShardRecord] = {}
        self._leases: dict[str, LeaseRecord] = {}
        self._checkpoints: dict[str, CheckpointRecord] = {}
        self._errors: dict[str, ErrorRecord] = {}
        self._manifests: dict[str, ManifestRecord] = {}
        self._edges: list[LineageEdge] = []

    def ensure_run(
        self, run_id: str, generation_id: str, config_fingerprint: str, now: float
    ) -> RunRecord:
        require_token(run_id, "run_id")
        require_token(generation_id, "generation_id")
        require_token(config_fingerprint, "config_fingerprint")
        existing = self._runs.get(run_id)
        if existing is not None:
            if existing.generation_id != generation_id:
                raise ValueError(f"run {run_id} already has generation {existing.generation_id}")
            if existing.config_fingerprint != config_fingerprint:
                raise ValueError(f"run {run_id} configuration is immutable")
            return existing
        record = RunRecord(run_id, generation_id, "pending", config_fingerprint, now, now)
        self._runs[run_id] = record
        return record

    def transition_run(self, run_id: str, status: str, now: float) -> RunRecord:
        current = self._runs[run_id]
        require_transition("run", current.status, status)
        updated = replace(current, status=status, updated_at=now)
        self._runs[run_id] = updated
        return updated

    def ensure_stage(self, run_id: str, stage: str, stage_version: str, now: float) -> StageRecord:
        require_token(stage, "stage")
        require_token(stage_version, "stage_version")
        for record in self._stages.values():
            if record.run_id == run_id and record.stage == stage:
                if record.stage_version != stage_version:
                    raise ValueError(f"stage {stage} version is immutable for run {run_id}")
                return record
        record = StageRecord(uuid4().hex, run_id, stage, stage_version, "pending", now, now)
        self._stages[record.stage_run_id] = record
        return record

    def transition_stage(self, stage_run_id: str, status: str, now: float) -> StageRecord:
        current = self._stages[stage_run_id]
        require_transition("stage", current.status, status)
        updated = replace(current, status=status, updated_at=now)
        self._stages[stage_run_id] = updated
        return updated

    def next_attempt(self, reuse_key: str) -> int:
        attempts = [item.attempt for item in self._shards.values() if item.reuse_key == reuse_key]
        return max(attempts, default=0) + 1

    def add_shard(self, record: ShardRecord) -> ShardRecord:
        attempt = (
            max(
                (
                    item.attempt
                    for item in self._shards.values()
                    if item.reuse_key == record.reuse_key
                ),
                default=0,
            )
            + 1
        )
        assigned = replace(record, attempt=attempt)
        self._shards[assigned.shard_run_id] = assigned
        return assigned

    def get_shard(self, shard_run_id: str) -> ShardRecord:
        return self._shards[shard_run_id]

    def reusable_shard(self, reuse_key: str) -> ShardRecord | None:
        matches = [
            item
            for item in self._shards.values()
            if item.reuse_key == reuse_key
            and item.status in {"succeeded", "quarantined"}
            and item.directory
            and not item.cache_hit
        ]
        return (
            None if not matches else max(matches, key=lambda item: (item.attempt, item.updated_at))
        )

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
        current = self._shards[shard_run_id]
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
        self._shards[shard_run_id] = updated
        return updated

    def shards(self) -> tuple[ShardRecord, ...]:
        return tuple(self._shards.values())

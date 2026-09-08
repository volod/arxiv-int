"""In-memory records for run, stage, shard, lease, checkpoint, error, and lineage."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from arxiv_int.interfaces.stores import TransformationRunRef, ValidationResultRef
from arxiv_int.interfaces.tokens import require_token
from arxiv_int.pipeline.control.fingerprints import ReuseIdentity
from arxiv_int.pipeline.control.quality import QualityCheck
from arxiv_int.pipeline.control.states import (
    FailureClass,
    LeaseStatus,
    ManifestStatus,
    ShardStatus,
)


@dataclass(frozen=True, slots=True)
class RunRecord:
    """One immutable requested configuration and output generation."""

    run_id: str
    generation_id: str
    status: str
    config_fingerprint: str
    created_at: float
    updated_at: float


@dataclass(frozen=True, slots=True)
class StageRecord:
    """One stage execution belonging to a run."""

    stage_run_id: str
    run_id: str
    stage: str
    stage_version: str
    status: str
    created_at: float
    updated_at: float


@dataclass(frozen=True, slots=True)
class ShardRecord:
    """One shard attempt with a deterministic reuse key."""

    shard_run_id: str
    stage_run_id: str
    run_id: str
    shard_id: str
    attempt: int
    reuse_key: str
    identity: ReuseIdentity
    status: ShardStatus
    lease_id: str | None
    cache_hit: bool
    created_at: float
    updated_at: float
    directory: str | None = None
    quality_warnings: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class LeaseRecord:
    """Exclusive work lease for one reuse key."""

    lease_id: str
    reuse_key: str
    holder_shard_run_id: str
    status: LeaseStatus
    acquired_at: float
    heartbeat_at: float
    expires_at: float


@dataclass(frozen=True, slots=True)
class CheckpointRecord:
    """Durable progress marker for a running shard."""

    checkpoint_id: str
    shard_run_id: str
    sequence: int
    payload_digest: str
    created_at: float


@dataclass(frozen=True, slots=True)
class ErrorRecord:
    """Bounded, classified failure evidence for one attempt."""

    error_id: str
    shard_run_id: str
    attempt: int
    code: str
    failure_class: FailureClass
    detail: str
    created_at: float


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    """Ledger pointer at one accepted or rejected attempt manifest."""

    manifest_id: str
    shard_run_id: str
    attempt: int
    reuse_key: str
    relative_path: str
    status: ManifestStatus
    sha256: str
    byte_count: int
    created_at: float


@dataclass(frozen=True, slots=True)
class ShardWork:
    """Inputs required to schedule or reuse one shard."""

    run_id: str
    generation_id: str
    stage: str
    stage_version: str
    shard_id: str
    config_fingerprint: str
    identity: ReuseIdentity
    checks: tuple[QualityCheck, ...] = ()
    validations: tuple[ValidationResultRef, ...] = ()
    transformations: tuple[TransformationRunRef, ...] = ()
    row_counts: Mapping[str, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_token(self.run_id, "run_id")
        require_token(self.generation_id, "generation_id")
        require_token(self.config_fingerprint, "config_fingerprint")
        frozen = {str(key): int(value) for key, value in self.row_counts.items()}
        object.__setattr__(self, "row_counts", MappingProxyType(frozen))

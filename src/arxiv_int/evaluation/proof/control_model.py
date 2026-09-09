"""Path-free records of one pipeline-control proof scenario."""

from collections.abc import Mapping
from dataclasses import dataclass

from arxiv_int.evaluation.proof.control_copy import ImmutabilitySnapshot


@dataclass(frozen=True, slots=True)
class ShardDelta:
    """Affected versus cached content-hash shards for one source mutation."""

    kind: str
    kinds: tuple[str, ...]
    invoked: tuple[str, ...]
    cached: tuple[str, ...]
    tombstone_hashes: tuple[str, ...]
    retracted: int
    last_occurrence: int
    active_rows: int


@dataclass(frozen=True, slots=True)
class ControlScenarioReport:
    """Acceptance evidence for the pipeline-control proof, without source paths."""

    proof_id: str
    forecast_decision: str
    forecast_confidence: str
    resume_ok: bool
    noop_worker_invocations: int
    deltas: Mapping[str, ShardDelta]
    invalidation_marked: int
    bump_alpha_invoked: int
    bump_preflight_cache_hits: int
    space_refused: bool
    rebuild_match: bool
    sole_recovery_blocked: bool
    prune_removed: int
    prune_eligible: int
    source_before: ImmutabilitySnapshot
    source_after: ImmutabilitySnapshot
    preflight_validated: bool
    artifact_checksums: Mapping[str, Mapping[str, int | str]]

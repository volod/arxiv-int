"""Typed inspection document for one run or dataset."""

from dataclasses import dataclass

SCHEMA_ID = "arxiv-int.inspect.v1"
DEFAULT_LIMIT = 5
DEVELOPMENT_ALIASES = frozenset({"local"})
LATEST_TOKEN = "latest"
CONFORMANCE_MATCHING = "matching"
CONFORMANCE_DRIFTED = "drifted"
CONFORMANCE_UNREGISTERED = "unregistered"
KIND_RUN = "run"
KIND_DATASET = "dataset"


@dataclass(frozen=True, slots=True)
class FileSummary:
    """One published sibling file with retained checksums."""

    name: str
    bytes: int
    sha256: str
    row_count: int | None
    valid: bool


@dataclass(frozen=True, slots=True)
class PartitionSummary:
    """One logical dataset partition without generation-specific paths."""

    dataset: str
    contract_version: str
    partition: tuple[tuple[str, str], ...]
    generation_id: str
    conformance: str
    bytes: int
    row_count: int | None


@dataclass(frozen=True, slots=True)
class QualityRuleSummary:
    """One retained Pandera, dbt, or fixture check without rerunning it."""

    rule_id: str
    scope: str
    status: str
    failed_count: int
    required: bool


@dataclass(frozen=True, slots=True)
class LineageSummary:
    """Sanitized transformation identity retained beside a producer."""

    command: str
    status: str
    input_fingerprint: str
    model_fingerprint: str
    activatable: bool


@dataclass(frozen=True, slots=True)
class AnchorSummary:
    """Bounded source coordinates; relative paths only."""

    silo_id: str
    relative_path: str
    scan_id: str
    kind: str
    page: int | None
    sheet: str
    cell_range: str


@dataclass(frozen=True, slots=True)
class StageSummary:
    """One stage's published attempt, quality, and honest outcome."""

    stage: str
    status: str
    outcome: str
    shard_id: str
    attempt: int
    cache_hit: bool
    bytes: int
    directory: str
    files: tuple[FileSummary, ...]
    partitions: tuple[PartitionSummary, ...]
    quality: tuple[QualityRuleSummary, ...]
    lineage: tuple[LineageSummary, ...]
    anchors: tuple[AnchorSummary, ...]
    quarantines: tuple[str, ...]
    failures: tuple[str, ...]
    schema_drifted: bool
    tree_valid: bool


@dataclass(frozen=True, slots=True)
class InspectionSummary:
    """Secret-free operator view of retained artifacts."""

    schema: str
    kind: str
    target: str
    run_id: str
    generation_id: str
    profile: str
    halted: bool
    halt_reason: str
    stages: tuple[StageSummary, ...]
    lake: tuple[PartitionSummary, ...]
    not_selected: tuple[str, ...]
    published_quality: tuple[QualityRuleSummary, ...]
    published_lineage: tuple[LineageSummary, ...]
    limit: int

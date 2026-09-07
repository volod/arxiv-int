"""Typed forecast decision document."""

from dataclasses import dataclass

SCHEMA_ID = "arxiv-int.forecast.v1"
DECISIONS = ("ready", "degraded", "blocked", "unknown")
CONFIDENCE = ("low", "medium", "high")


@dataclass(frozen=True, slots=True)
class ByteRange:
    """Inclusive lower and upper byte estimates."""

    lower: int
    upper: int


@dataclass(frozen=True, slots=True)
class TimeRange:
    """Inclusive wall-clock seconds range; never a single invented duration."""

    lower_seconds: float
    upper_seconds: float


@dataclass(frozen=True, slots=True)
class WorkCounts:
    """Per-stage inventory and cache-hit counts."""

    input_files: int
    input_bytes: int
    added: int
    changed: int
    renamed: int
    removed: int
    cached: int
    recomputed: int


@dataclass(frozen=True, slots=True)
class OutputCosts:
    """Lower/upper bytes for persistent outputs and peak scratch families."""

    normalized: ByteRange
    database_heap: ByteRange
    indexes: ByteRange
    vectors: ByteRange
    graph: ByteRange
    artifacts: ByteRange
    logs: ByteRange
    backups: ByteRange
    wal: ByteRange
    temp: ByteRange
    staging: ByteRange
    rebuild: ByteRange
    rollback: ByteRange


@dataclass(frozen=True, slots=True)
class StageForecast:
    """One planned stage's work, ranges, and local decision."""

    stage: str
    work: WorkCounts
    output_bytes: ByteRange
    time: TimeRange
    peak_bytes: ByteRange
    decision: str
    confidence: str
    cache_hit: bool
    gpu_required: bool
    actions: tuple[str, ...]
    evidence: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DeviceBudget:
    """One filesystem device after root deduplication."""

    device_id: str
    roots: tuple[str, ...]
    path: str
    filesystem: str
    storage_classes: tuple[str, ...]
    rotational: bool | None
    free_bytes: int
    accessible: bool
    peak: ByteRange
    reserve_bytes: int
    decision: str
    actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Coefficient:
    """One numeric bound and the evidence that produced it."""

    name: str
    value: float
    source: str
    evidence_id: str


@dataclass(frozen=True, slots=True)
class HostAssumptions:
    """CPU/GPU/RAM snapshot used as assumptions, not a model-load probe."""

    ram_available_gib: float
    gpu_name: str
    gpu_total_gib: float
    device_id: str
    workers: int


@dataclass(frozen=True, slots=True)
class ForecastDocument:
    """Fingerprinted console/JSON decision retained under a run or forecast id."""

    schema: str
    forecast_id: str
    run_id: str | None
    production: bool
    profile: str
    plan: tuple[str, ...]
    not_selected: tuple[str, ...]
    decision: str
    confidence: str
    fingerprint: str
    config_fingerprint: str
    source_snapshot: str
    envelope_fingerprint: str
    inventory_source: str
    stages: tuple[StageForecast, ...]
    devices: tuple[DeviceBudget, ...]
    outputs: OutputCosts
    time: TimeRange
    critical_path: tuple[str, ...]
    host: HostAssumptions
    coefficients: tuple[Coefficient, ...]
    actions: tuple[str, ...]
    excluded: tuple[str, ...]

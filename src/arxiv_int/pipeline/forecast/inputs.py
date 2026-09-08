"""Captured forecast inputs: inventory, cache, telemetry, devices, envelope."""

from collections.abc import Mapping
from dataclasses import dataclass

from arxiv_int.pipeline.forecast.model import HostAssumptions
from arxiv_int.pipeline.registry import ResourceEstimate


@dataclass(frozen=True, slots=True)
class InventoryEvidence:
    """Sampled or manifested archive counts used by the estimator."""

    files: int
    bytes: int
    added: int
    changed: int
    renamed: int
    removed: int
    formats: Mapping[str, tuple[int, int]]
    source: str
    truncated: bool
    fingerprint: str

    def __post_init__(self) -> None:
        frozen = {key: value for key, value in sorted(self.formats.items())}
        object.__setattr__(self, "formats", frozen)


@dataclass(frozen=True, slots=True)
class CacheHitPlan:
    """Per-stage cache hits derived from the reuse index."""

    hits: tuple[tuple[str, bool, int], ...] = ()

    def hit(self, stage: str) -> bool:
        """Return whether ``stage`` is a validated cache hit."""
        for name, cached, _size in self.hits:
            if name == stage:
                return cached
        return False

    def cached_bytes(self, stage: str) -> int:
        """Return previously published payload bytes for ``stage``."""
        for name, cached, size in self.hits:
            if name == stage and cached:
                return size
        return 0


@dataclass(frozen=True, slots=True)
class ComparableRun:
    """Prior-run telemetry used to bound time and output amplification."""

    run_id: str
    profile: str
    input_bytes: int
    stage_seconds: Mapping[str, float]
    stage_bytes: Mapping[str, int]


@dataclass(frozen=True, slots=True)
class DeviceSnapshot:
    """Inspected placement for one configured root."""

    variable: str
    path: str
    device_id: str
    filesystem: str
    storage_class: str
    rotational: bool | None
    free_bytes: int
    accessible: bool
    read_only: bool


@dataclass(frozen=True, slots=True)
class Envelope:
    """Declared conservative coefficients when measured evidence is absent."""

    amplification_lower: float
    amplification_upper: float
    safety_reserve_bytes: int
    safety_reserve_ratio: float
    sample_file_limit: int
    format_sample_limit: int
    large_input_bytes: int
    wal_fraction: float
    temp_fraction: float
    staging_fraction: float
    rebuild_multiplier: float
    rollback_fraction: float
    backup_fraction: float
    rotational_time_lower: float
    rotational_time_upper: float
    seconds_per_gib_lower: float
    seconds_per_gib_upper: float
    log_bytes_per_stage: int
    truncated_upper_factor: float
    families: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class ForecastInputs:
    """Captured evidence the pure estimator consumes."""

    forecast_id: str
    run_id: str | None
    production: bool
    profile: str
    plan: tuple[str, ...]
    not_selected: tuple[str, ...]
    config_fingerprint: str
    source_snapshot: str
    envelope: Envelope
    envelope_fingerprint: str
    inventory: InventoryEvidence
    cache: CacheHitPlan
    comparable: tuple[ComparableRun, ...]
    devices: tuple[DeviceSnapshot, ...]
    host: HostAssumptions
    estimates: Mapping[str, ResourceEstimate]
    gpu_stages: frozenset[str]

"""Shared forecast fixtures and captured-evidence builders."""

from pathlib import Path

from arxiv_int.pipeline.forecast.capacity import DEFAULT_ENVELOPE, envelope_fingerprint
from arxiv_int.pipeline.forecast.inputs import (
    CacheHitPlan,
    DeviceSnapshot,
    Envelope,
    ForecastInputs,
    InventoryEvidence,
)
from arxiv_int.pipeline.forecast.model import HostAssumptions
from arxiv_int.pipeline.registry import ResourceEstimate
from arxiv_int.runtime.filesystem import FilesystemEvidence

TEST_ENVELOPE = Envelope(
    amplification_lower=DEFAULT_ENVELOPE.amplification_lower,
    amplification_upper=DEFAULT_ENVELOPE.amplification_upper,
    safety_reserve_bytes=1_000,
    safety_reserve_ratio=0.05,
    sample_file_limit=DEFAULT_ENVELOPE.sample_file_limit,
    format_sample_limit=DEFAULT_ENVELOPE.format_sample_limit,
    large_input_bytes=DEFAULT_ENVELOPE.large_input_bytes,
    wal_fraction=DEFAULT_ENVELOPE.wal_fraction,
    temp_fraction=DEFAULT_ENVELOPE.temp_fraction,
    staging_fraction=DEFAULT_ENVELOPE.staging_fraction,
    rebuild_multiplier=DEFAULT_ENVELOPE.rebuild_multiplier,
    rollback_fraction=DEFAULT_ENVELOPE.rollback_fraction,
    backup_fraction=DEFAULT_ENVELOPE.backup_fraction,
    rotational_time_lower=DEFAULT_ENVELOPE.rotational_time_lower,
    rotational_time_upper=DEFAULT_ENVELOPE.rotational_time_upper,
    seconds_per_gib_lower=DEFAULT_ENVELOPE.seconds_per_gib_lower,
    seconds_per_gib_upper=DEFAULT_ENVELOPE.seconds_per_gib_upper,
    log_bytes_per_stage=DEFAULT_ENVELOPE.log_bytes_per_stage,
    truncated_upper_factor=DEFAULT_ENVELOPE.truncated_upper_factor,
    families=DEFAULT_ENVELOPE.families,
)


def make_inventory(
    *,
    files: int = 4,
    nbytes: int = 4_096,
    source: str = "sample",
    truncated: bool = False,
) -> InventoryEvidence:
    """Return captured inventory evidence for estimator tests."""
    formats = {"txt": (files, nbytes)}
    return InventoryEvidence(
        files=files,
        bytes=nbytes,
        added=files,
        changed=0,
        renamed=0,
        removed=0,
        formats=formats,
        source=source,
        truncated=truncated,
        fingerprint=f"inv-{files}-{nbytes}-{source}",
    )


def make_devices(
    *,
    free_bytes: int = 10**12,
    shared_results: bool = True,
    accessible: bool = True,
    rotational: bool | None = False,
) -> tuple[DeviceSnapshot, ...]:
    """Return archive/results/database snapshots with optional shared devices."""
    results_dev = "8:1"
    runs_dev = "8:1" if shared_results else "8:9"
    return (
        DeviceSnapshot(
            "ARCHIVE_DIR", "/archive", "8:0", "ext4", "source", False, free_bytes, accessible, True
        ),
        DeviceSnapshot(
            "RESULTS_DIR",
            "/results",
            results_dev,
            "ext4",
            "bulk",
            rotational,
            free_bytes,
            accessible,
            False,
        ),
        DeviceSnapshot(
            "RUNS_DIR", "/runs", runs_dev, "ext4", "bulk", rotational, free_bytes, accessible, False
        ),
        DeviceSnapshot(
            "PGDATA_DIR",
            "/pgdata",
            "8:2",
            "ext4",
            "database",
            rotational,
            free_bytes,
            accessible,
            False,
        ),
        DeviceSnapshot(
            "TMP_DIR", "/tmp", "8:3", "ext4", "scratch", rotational, free_bytes, accessible, False
        ),
        DeviceSnapshot(
            "SERVICE_STATE_DIR",
            "/svc",
            "8:1",
            "ext4",
            "service-state",
            False,
            free_bytes,
            accessible,
            False,
        ),
        DeviceSnapshot(
            "MODEL_CACHE_DIR",
            "/models",
            "8:1",
            "ext4",
            "model",
            False,
            free_bytes,
            accessible,
            False,
        ),
    )


def make_inputs(
    *,
    forecast_id: str = "forecast-test",
    run_id: str | None = "run-test",
    production: bool = True,
    profile: str = "fixture",
    plan: tuple[str, ...] = ("alpha", "beta", "gamma"),
    inventory: InventoryEvidence | None = None,
    devices: tuple[DeviceSnapshot, ...] | None = None,
    cache: CacheHitPlan | None = None,
    gpu: bool = False,
    envelope: Envelope | None = None,
    config_fingerprint: str = "cfg-1",
    source_snapshot: str = "snap-1",
) -> ForecastInputs:
    """Build captured estimator inputs without touching the filesystem."""
    chosen = envelope or TEST_ENVELOPE
    estimates = {name: ResourceEstimate(gpu_required=gpu and name == "gamma") for name in plan}
    return ForecastInputs(
        forecast_id=forecast_id,
        run_id=run_id,
        production=production,
        profile=profile,
        plan=plan,
        not_selected=("omega",),
        config_fingerprint=config_fingerprint,
        source_snapshot=source_snapshot,
        envelope=chosen,
        envelope_fingerprint=envelope_fingerprint(chosen),
        inventory=inventory or make_inventory(),
        cache=cache or CacheHitPlan(),
        comparable=(),
        devices=devices or make_devices(),
        host=HostAssumptions(
            16.0,
            "NVIDIA GeForce RTX 4060 Ti" if gpu else "none",
            16.0,
            "cuda:0" if gpu else "cpu",
            1,
        ),
        estimates=estimates,
        gpu_stages=frozenset({"gamma"} if gpu else ()),
    )


def plentiful_inspect(path: Path) -> FilesystemEvidence:
    """Return a writable device with enough free space for CLI tests."""
    return FilesystemEvidence(path, "ext4", "8:1", False, 10**18, True, False)

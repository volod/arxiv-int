"""Declared capacity coefficients and the committed envelope overlay."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.forecast.inputs import Envelope
from arxiv_int.resources.paths import configs_output_root, configs_root

ENVELOPE_NAME = "envelope.json"
SCHEMA_NAME = "forecast.schema.json"
ENVELOPE_SCHEMA = "arxiv-int.capacity.envelope.v1"
GIB = 1024**3

DEFAULT_FAMILIES: dict[str, float] = {
    "artifacts": 0.04,
    "backups": 0.0,
    "database_heap": 0.22,
    "graph": 0.05,
    "indexes": 0.14,
    "logs": 0.02,
    "normalized": 0.43,
    "vectors": 0.10,
}

DEFAULT_ENVELOPE = Envelope(
    amplification_lower=2.5,
    amplification_upper=4.0,
    safety_reserve_bytes=GIB,
    safety_reserve_ratio=0.05,
    sample_file_limit=10_000,
    format_sample_limit=200,
    large_input_bytes=50 * GIB,
    wal_fraction=0.25,
    temp_fraction=0.15,
    staging_fraction=0.20,
    rebuild_multiplier=1.0,
    rollback_fraction=0.20,
    backup_fraction=0.0,
    rotational_time_lower=1.5,
    rotational_time_upper=3.0,
    seconds_per_gib_lower=20.0,
    seconds_per_gib_upper=240.0,
    log_bytes_per_stage=1_048_576,
    truncated_upper_factor=2.0,
    families=DEFAULT_FAMILIES,
)


def envelope_payload(envelope: Envelope = DEFAULT_ENVELOPE) -> dict[str, Any]:
    """Serialize one envelope for the committed config file."""
    return {
        "amplification_lower": envelope.amplification_lower,
        "amplification_upper": envelope.amplification_upper,
        "backup_fraction": envelope.backup_fraction,
        "families": dict(envelope.families),
        "format_sample_limit": envelope.format_sample_limit,
        "large_input_bytes": envelope.large_input_bytes,
        "log_bytes_per_stage": envelope.log_bytes_per_stage,
        "rebuild_multiplier": envelope.rebuild_multiplier,
        "rollback_fraction": envelope.rollback_fraction,
        "rotational_time_lower": envelope.rotational_time_lower,
        "rotational_time_upper": envelope.rotational_time_upper,
        "safety_reserve_bytes": envelope.safety_reserve_bytes,
        "safety_reserve_ratio": envelope.safety_reserve_ratio,
        "sample_file_limit": envelope.sample_file_limit,
        "schema": ENVELOPE_SCHEMA,
        "seconds_per_gib_lower": envelope.seconds_per_gib_lower,
        "seconds_per_gib_upper": envelope.seconds_per_gib_upper,
        "staging_fraction": envelope.staging_fraction,
        "temp_fraction": envelope.temp_fraction,
        "truncated_upper_factor": envelope.truncated_upper_factor,
        "wal_fraction": envelope.wal_fraction,
    }


def envelope_from_payload(payload: Mapping[str, Any]) -> Envelope:
    """Build an envelope from a JSON object, filling unspecified fields from defaults."""
    families = payload.get("families", DEFAULT_FAMILIES)
    if not isinstance(families, dict):
        families = DEFAULT_FAMILIES
    parsed = {str(key): float(value) for key, value in families.items()}
    return Envelope(
        amplification_lower=float(payload.get("amplification_lower", 2.5)),
        amplification_upper=float(payload.get("amplification_upper", 4.0)),
        safety_reserve_bytes=int(payload.get("safety_reserve_bytes", GIB)),
        safety_reserve_ratio=float(payload.get("safety_reserve_ratio", 0.05)),
        sample_file_limit=int(payload.get("sample_file_limit", 10_000)),
        format_sample_limit=int(payload.get("format_sample_limit", 200)),
        large_input_bytes=int(payload.get("large_input_bytes", 50 * GIB)),
        wal_fraction=float(payload.get("wal_fraction", 0.25)),
        temp_fraction=float(payload.get("temp_fraction", 0.15)),
        staging_fraction=float(payload.get("staging_fraction", 0.20)),
        rebuild_multiplier=float(payload.get("rebuild_multiplier", 1.0)),
        rollback_fraction=float(payload.get("rollback_fraction", 0.20)),
        backup_fraction=float(payload.get("backup_fraction", 0.0)),
        rotational_time_lower=float(payload.get("rotational_time_lower", 1.5)),
        rotational_time_upper=float(payload.get("rotational_time_upper", 3.0)),
        seconds_per_gib_lower=float(payload.get("seconds_per_gib_lower", 20.0)),
        seconds_per_gib_upper=float(payload.get("seconds_per_gib_upper", 240.0)),
        log_bytes_per_stage=int(payload.get("log_bytes_per_stage", 1_048_576)),
        truncated_upper_factor=float(payload.get("truncated_upper_factor", 2.0)),
        families=parsed,
    )


def envelope_fingerprint(envelope: Envelope) -> str:
    """Fingerprint declared coefficients so a changed envelope cannot reuse a forecast."""
    return sha256_text(normalize_json(envelope_payload(envelope)))


def load_envelope(project_root: Path | None = None) -> Envelope:
    """Load packaged ``configs/capacity/envelope.json`` when present; otherwise use defaults."""
    path = configs_root(project_root) / "capacity" / ENVELOPE_NAME
    if not path.is_file():
        return DEFAULT_ENVELOPE
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} is not a JSON object")
    return envelope_from_payload(loaded)


def write_envelope(project_root: Path, envelope: Envelope = DEFAULT_ENVELOPE) -> Path:
    """Write the committed envelope overlay."""
    directory = configs_output_root(project_root) / "capacity"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / ENVELOPE_NAME
    path.write_text(normalize_json(envelope_payload(envelope)), encoding="utf-8")
    return path

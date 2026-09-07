"""Canonical run-bundle manifest identity, schema, and fingerprinting."""

import json
import math
import re
from collections.abc import Mapping
from pathlib import PurePosixPath

from arxiv_int.evaluation.bundle_errors import BundleManifestError
from arxiv_int.evaluation.bundle_layout import (
    MANIFEST_NAME,
    digest_bytes,
    parse_artifact_name,
)

SCHEMA_VERSION = 1
MANIFEST_MAX_BYTES = 1_048_576
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_REQUIRED = (
    "schema_version",
    "run_id",
    "kind",
    "input_fingerprints",
    "configuration",
    "metrics",
    "verdict",
    "artifacts",
)


def canonical_json(payload: object) -> bytes:
    """Serialize a manifest object with stable ASCII, keys, and a trailing newline."""
    return (json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()


def json_line(payload: object) -> bytes:
    """Serialize one JSONL object with stable keys."""
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def identity_text(field: str, value: object) -> str:
    """Require a non-empty identity string without surrounding whitespace or NULs."""
    if not isinstance(value, str) or not value or "\x00" in value or "\n" in value:
        raise BundleManifestError(f"run-bundle manifest {field} is missing or malformed")
    if value.strip() != value:
        raise BundleManifestError(f"run-bundle manifest {field} is missing or malformed")
    return value


def finite_number(field: str, value: object) -> float:
    """Require a finite JSON number, rejecting bool which subclasses int."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise BundleManifestError(f"run-bundle manifest {field} is missing or malformed")
    return float(value)


def string_map(field: str, value: object) -> dict[str, str]:
    """Require a string-to-string map with identity keys and values."""
    if not isinstance(value, dict):
        raise BundleManifestError(f"run-bundle manifest {field} is missing or malformed")
    items = sorted(value.items())
    return {
        identity_text(f"{field} key", key): identity_text(f"{field}[{key}]", item)
        for key, item in items
    }


def object_map(field: str, value: object) -> dict[str, object]:
    """Require a JSON object with identity keys."""
    if not isinstance(value, dict):
        raise BundleManifestError(f"run-bundle manifest {field} is missing or malformed")
    return {identity_text(f"{field} key", key): item for key, item in value.items()}


def metric_map(value: object) -> dict[str, float]:
    """Require finite numeric metrics keyed by identity strings."""
    if not isinstance(value, dict):
        raise BundleManifestError("run-bundle manifest metrics is missing or malformed")
    return {
        identity_text("metrics key", key): finite_number(f"metrics[{key}]", item)
        for key, item in sorted(value.items())
    }


def artifact_registry(value: object) -> dict[str, dict[str, int | str]]:
    """Require relative artifact names with sha256 and byte counts."""
    if not isinstance(value, dict) or not value:
        raise BundleManifestError("run-bundle manifest has no artifact registry")
    registry: dict[str, dict[str, int | str]] = {}
    for raw_name, record in value.items():
        name = parse_artifact_name(str(raw_name) if isinstance(raw_name, str) else "").as_posix()
        registry[name] = _artifact_record(name, record)
    return registry


def build_manifest(
    *,
    run_id: str,
    kind: str,
    input_fingerprints: Mapping[str, str],
    configuration: Mapping[str, object],
    metrics: Mapping[str, float],
    verdict: str,
    artifacts: Mapping[str, tuple[str, int]],
) -> dict[str, object]:
    """Build the schema-version-1 manifest object for a published run."""
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": identity_text("run_id", run_id),
        "kind": identity_text("kind", kind),
        "input_fingerprints": string_map("input_fingerprints", dict(input_fingerprints)),
        "configuration": object_map("configuration", dict(configuration)),
        "metrics": metric_map(dict(metrics)),
        "verdict": identity_text("verdict", verdict),
        "artifacts": {
            name: {"bytes": size, "sha256": digest}
            for name, (digest, size) in sorted(artifacts.items())
        },
    }


def parse_manifest_bytes(raw: bytes) -> dict[str, object]:
    """Parse, type-check, and require canonical encoding of a manifest payload."""
    if len(raw) > MANIFEST_MAX_BYTES:
        raise BundleManifestError(f"{MANIFEST_NAME} exceeds {MANIFEST_MAX_BYTES} bytes")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise BundleManifestError("run-bundle manifest is not valid JSON") from error
    parsed = validate_manifest(payload)
    if canonical_json(parsed) != raw:
        raise BundleManifestError("run-bundle manifest is not canonical")
    return parsed


def validate_manifest(payload: object) -> dict[str, object]:
    """Return a canonical manifest object or raise a typed identity failure."""
    if not isinstance(payload, dict):
        raise BundleManifestError("run-bundle manifest is not an object")
    extra = sorted(set(payload) - set(_REQUIRED))
    missing = [field for field in _REQUIRED if field not in payload]
    if extra or missing:
        raise BundleManifestError("run-bundle manifest identities are missing or malformed")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise BundleManifestError("unsupported run-bundle schema version")
    artifacts = artifact_registry(payload["artifacts"])
    return {
        "artifacts": artifacts,
        "configuration": object_map("configuration", payload["configuration"]),
        "input_fingerprints": string_map("input_fingerprints", payload["input_fingerprints"]),
        "kind": identity_text("kind", payload["kind"]),
        "metrics": metric_map(payload["metrics"]),
        "run_id": identity_text("run_id", payload["run_id"]),
        "schema_version": SCHEMA_VERSION,
        "verdict": identity_text("verdict", payload["verdict"]),
    }


def manifest_fingerprint(raw: bytes) -> str:
    """Return the SHA-256 hex digest of on-disk canonical manifest bytes."""
    return digest_bytes(raw)


def artifact_path(name: str) -> PurePosixPath:
    """Return the contained relative path recorded for one manifest artifact."""
    return parse_artifact_name(name)


def _artifact_record(name: str, record: object) -> dict[str, int | str]:
    if not isinstance(record, dict):
        raise BundleManifestError(f"invalid artifact record: {name!r}")
    digest = record.get("sha256")
    size = record.get("bytes")
    if not isinstance(digest, str) or _SHA256.fullmatch(digest) is None:
        raise BundleManifestError(f"invalid artifact record: {name!r}")
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise BundleManifestError(f"invalid artifact record: {name!r}")
    extra = set(record) - {"sha256", "bytes"}
    if extra:
        raise BundleManifestError(f"invalid artifact record: {name!r}")
    return {"bytes": size, "sha256": digest}


def expected_files(artifacts: Mapping[str, object]) -> set[str]:
    """Return the file set a verified bundle must contain exactly."""
    return {MANIFEST_NAME, *artifacts}


def load_manifest(raw: bytes) -> tuple[dict[str, object], str]:
    """Parse canonical manifest bytes and return the object plus fingerprint."""
    parsed = parse_manifest_bytes(raw)
    return parsed, manifest_fingerprint(raw)


def artifact_records(payload: Mapping[str, object]) -> dict[str, dict[str, int | str]]:
    """Return the typed artifact registry from a validated manifest."""
    artifacts = payload["artifacts"]
    if not isinstance(artifacts, dict):
        raise BundleManifestError("run-bundle manifest has no artifact registry")
    return {str(name): _artifact_record(str(name), record) for name, record in artifacts.items()}

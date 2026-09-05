"""Atomic, immutable, checksum-verified evaluation run bundles."""

import hashlib
import json
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Literal

SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class BundleSpec:
    """The identity, inputs, configuration, and results of one evaluation run."""

    run_id: str
    kind: str
    input_fingerprints: Mapping[str, str]
    configuration: Mapping[str, object]
    metrics: Mapping[str, float]
    verdict: str


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    """One immutable file named by a run manifest."""

    sha256: str
    bytes: int


@dataclass(frozen=True, slots=True)
class PublishedBundle:
    """Paths and manifest fingerprint of an atomically published bundle."""

    directory: Path
    manifest: Path
    fingerprint: str


def _digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _canonical_json(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()


def _json_line(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True) + "\n"
    ).encode()


def _artifact_name(name: str) -> PurePosixPath:
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(f"invalid bundle artifact name: {name!r}")
    if path == PurePosixPath("manifest.json"):
        raise ValueError("manifest.json is reserved")
    return path


def _write(path: Path, payload: bytes) -> ArtifactRecord:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return ArtifactRecord(_digest(payload), len(payload))


def _manifest(spec: BundleSpec, artifacts: Mapping[str, ArtifactRecord]) -> dict[str, object]:
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": spec.run_id,
        "kind": spec.kind,
        "input_fingerprints": dict(sorted(spec.input_fingerprints.items())),
        "configuration": dict(spec.configuration),
        "metrics": dict(sorted(spec.metrics.items())),
        "verdict": spec.verdict,
        "artifacts": {
            name: {"sha256": record.sha256, "bytes": record.bytes}
            for name, record in sorted(artifacts.items())
        },
    }


def publish_run_bundle(
    directory: Path,
    spec: BundleSpec,
    case_rows: Sequence[Mapping[str, object]],
    *,
    artifacts: Mapping[str, str | bytes] | None = None,
) -> PublishedBundle:
    """Write, verify, and atomically publish a bundle without replacing evidence."""
    directory = Path(directory)
    if directory.exists():
        raise FileExistsError(f"run bundle already exists: {directory}")
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=directory.parent, prefix=f".{directory.name}.tmp-"))
    try:
        records: dict[str, ArtifactRecord] = {}
        score_bytes = b"".join(_json_line(dict(row)) for row in case_rows)
        records["scores.jsonl"] = _write(staging / "scores.jsonl", score_bytes)
        for raw_name, content in (artifacts or {}).items():
            name = _artifact_name(raw_name).as_posix()
            if name in records:
                raise ValueError(f"duplicate bundle artifact name: {name!r}")
            payload = content.encode() if isinstance(content, str) else content
            records[name] = _write(staging.joinpath(*PurePosixPath(name).parts), payload)
        manifest_bytes = _canonical_json(_manifest(spec, records))
        _write(staging / "manifest.json", manifest_bytes)
        verify_run_bundle(staging)
        os.replace(staging, directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return PublishedBundle(directory, directory / "manifest.json", _digest(manifest_bytes))


def verify_run_bundle(directory: Path) -> Literal[True]:
    """Refuse a missing, corrupt, or unregistered file in a published bundle."""
    directory = Path(directory)
    manifest_path = directory / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported run-bundle schema version")
    raw_artifacts = payload.get("artifacts")
    if not isinstance(raw_artifacts, dict):
        raise ValueError("run-bundle manifest has no artifact registry")
    expected = {"manifest.json", *raw_artifacts}
    actual = {
        path.relative_to(directory).as_posix() for path in directory.rglob("*") if path.is_file()
    }
    if actual != expected:
        raise ValueError(f"run-bundle files do not match manifest: {sorted(actual ^ expected)}")
    for name, record in raw_artifacts.items():
        if not isinstance(record, dict):
            raise ValueError(f"invalid artifact record: {name!r}")
        data = directory.joinpath(*_artifact_name(name).parts).read_bytes()
        if record.get("bytes") != len(data) or record.get("sha256") != _digest(data):
            raise ValueError(f"run-bundle artifact failed verification: {name}")
    return True

"""Atomic sibling writes for run manifests; partial trees are never accepted."""

import hashlib
import json
import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.interfaces.tokens import require_relative_path, require_token

MANIFEST_NAME = "manifest.json"
TMP_PREFIX = "."
TMP_SUFFIX = ".tmp"
HASH_CHUNK_BYTES = 1_048_576
Injector = Callable[[str], None]


class ArtifactPublishError(RuntimeError):
    """Raised when a staged tree cannot be accepted."""


class InjectedCrash(RuntimeError):
    """Test-only interrupt at a named publication point."""


@dataclass(frozen=True, slots=True)
class FileRecord:
    """Checksum and size of one published sibling file."""

    sha256: str
    bytes: int
    row_count: int | None = None


@dataclass(frozen=True, slots=True)
class ArtifactManifest:
    """Accepted file set for one shard attempt."""

    reuse_key: str
    attempt: int
    files: Mapping[str, FileRecord]
    directory: Path


def attempt_directory(runs_dir: Path, run_id: str, stage: str, shard_id: str, attempt: int) -> Path:
    """Return ``$RUNS_DIR/<run-id>/manifests/<stage>/<shard>/attempt-<n>/``."""
    require_token(run_id, "run_id")
    require_token(stage, "stage")
    require_token(shard_id, "shard_id")
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    return runs_dir / run_id / "manifests" / stage / shard_id / f"attempt-{attempt}"


def publish_attempt(
    directory: Path,
    *,
    reuse_key: str,
    attempt: int,
    files: Mapping[str, bytes],
    row_counts: Mapping[str, int] | None = None,
    injector: Injector | None = None,
) -> ArtifactManifest:
    """Write sibling temp files, validate, then atomically rename; manifest last."""
    require_token(reuse_key, "reuse_key")
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    if not files:
        raise ArtifactPublishError("refusing to publish an empty artifact set")
    names = tuple(sorted(files))
    for name in names:
        _require_artifact_name(name)
    directory.mkdir(parents=True, exist_ok=True)
    records = {name: _write_sibling(directory, name, files[name], injector) for name in names}
    _hit(injector, "after-payload-write")
    counts = dict(row_counts or {})
    payload = {
        "attempt": attempt,
        "files": {
            name: {
                "bytes": records[name].bytes,
                "rowCount": counts.get(name),
                "sha256": records[name].sha256,
            }
            for name in names
        },
        "reuseKey": reuse_key,
    }
    manifest_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8") + b"\n"
    manifest_tmp = _tmp_path(directory, MANIFEST_NAME)
    _write_bytes(manifest_tmp, manifest_bytes)
    _hit(injector, "after-manifest-write")
    for name in names:
        os.replace(_tmp_path(directory, name), directory / name)
    _hit(injector, "after-payload-rename")
    os.replace(manifest_tmp, directory / MANIFEST_NAME)
    accepted = {
        name: FileRecord(records[name].sha256, records[name].bytes, counts.get(name))
        for name in names
    }
    return ArtifactManifest(reuse_key, attempt, accepted, directory)


def validate_attempt(directory: Path, *, reuse_key: str, attempt: int) -> ArtifactManifest:
    """Accept a tree only when the manifest and every checksum still match."""
    files = _load_manifest_files(directory, reuse_key, attempt)
    accepted = _checksum_files(directory, files)
    extra = {
        item.name
        for item in directory.iterdir()
        if item.is_file() and item.name not in accepted and item.name != MANIFEST_NAME
    }
    if extra:
        raise ArtifactPublishError("unregistered files are present: " + ", ".join(sorted(extra)))
    return ArtifactManifest(reuse_key, attempt, accepted, directory)


def _load_manifest_files(directory: Path, reuse_key: str, attempt: int) -> dict[str, object]:
    manifest_path = directory / MANIFEST_NAME
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise ArtifactPublishError(f"attempt manifest is missing: {directory}")
    loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ArtifactPublishError("attempt manifest is not an object")
    if loaded.get("reuseKey") != reuse_key or int(loaded.get("attempt") or 0) != attempt:
        raise ArtifactPublishError("attempt manifest identity does not match the ledger")
    files = loaded.get("files")
    if not isinstance(files, dict) or not files:
        raise ArtifactPublishError("attempt manifest has no files")
    return files


def _checksum_files(directory: Path, files: dict[str, object]) -> dict[str, FileRecord]:
    accepted: dict[str, FileRecord] = {}
    for name, spec in files.items():
        _require_artifact_name(str(name))
        if not isinstance(spec, dict):
            raise ArtifactPublishError(f"manifest entry {name!r} is not an object")
        path = directory / str(name)
        if path.is_symlink() or not path.is_file():
            raise ArtifactPublishError(f"published file is missing: {name}")
        digest, size = _hash_file(path)
        expected_digest = str(spec.get("sha256") or "")
        expected_size = int(spec.get("bytes") or -1)
        if digest != expected_digest or size != expected_size:
            raise ArtifactPublishError(f"checksum mismatch for {name}")
        row_count = spec.get("rowCount")
        accepted[str(name)] = FileRecord(
            digest, size, None if row_count is None else int(row_count)
        )
    return accepted


def _require_artifact_name(name: str) -> None:
    if name == MANIFEST_NAME:
        raise ArtifactPublishError("manifest.json is reserved")
    require_relative_path(name, "artifact")
    if name.startswith(TMP_PREFIX) or name.endswith(TMP_SUFFIX):
        raise ArtifactPublishError(f"refusing temp-shaped artifact name {name!r}")


def _tmp_path(directory: Path, name: str) -> Path:
    return directory / f"{TMP_PREFIX}{name}{TMP_SUFFIX}"


def _write_sibling(
    directory: Path, name: str, payload: bytes, injector: Injector | None
) -> FileRecord:
    path = _tmp_path(directory, name)
    digest, size = _write_bytes(path, payload)
    _hit(injector, f"after-write:{name}")
    return FileRecord(digest, size, None)


def _write_bytes(path: Path, payload: bytes) -> tuple[str, int]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())
    return sha256_text_bytes(payload), len(payload)


def sha256_text_bytes(payload: bytes) -> str:
    """Return the SHA-256 digest of raw bytes without newline normalization."""
    return hashlib.sha256(payload).hexdigest()


def _hash_file(path: Path) -> tuple[str, int]:
    hasher = hashlib.sha256()
    total = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(HASH_CHUNK_BYTES)
            if not chunk:
                break
            hasher.update(chunk)
            total += len(chunk)
    return hasher.hexdigest(), total


def _hit(injector: Injector | None, point: str) -> None:
    if injector is not None:
        injector(point)

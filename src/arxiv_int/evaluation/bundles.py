"""Atomic, immutable, checksum-verified evaluation run bundles."""

import hashlib
import logging
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from arxiv_int.evaluation.bundle_errors import BundleExistsError, BundleIntegrityError
from arxiv_int.evaluation.bundle_layout import (
    MANIFEST_NAME,
    SCORES_NAME,
    digest_fd,
    exclusive_publish,
    extra_artifact_name,
    list_bundle_tree,
    open_contained_file,
    parent_directories,
    read_capped,
    write_payload,
)
from arxiv_int.evaluation.bundle_manifest import (
    MANIFEST_MAX_BYTES,
    artifact_path,
    artifact_records,
    build_manifest,
    canonical_json,
    expected_files,
    identity_text,
    json_line,
    load_manifest,
    metric_map,
    object_map,
    string_map,
)

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class BundleSpec:
    """The identity, inputs, configuration, and results of one evaluation run."""

    run_id: str
    kind: str
    input_fingerprints: Mapping[str, str]
    configuration: Mapping[str, object]
    metrics: Mapping[str, float]
    verdict: str

    def __post_init__(self) -> None:
        identity_text("run_id", self.run_id)
        identity_text("kind", self.kind)
        identity_text("verdict", self.verdict)
        string_map("input_fingerprints", dict(self.input_fingerprints))
        object_map("configuration", dict(self.configuration))
        metric_map(dict(self.metrics))


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


def publish_run_bundle(
    directory: Path,
    spec: BundleSpec,
    case_rows: Sequence[Mapping[str, object]],
    *,
    artifacts: Mapping[str, str | bytes] | None = None,
) -> PublishedBundle:
    """Write, verify, and atomically publish a bundle without replacing evidence."""
    directory = Path(directory)
    if directory.is_symlink() or directory.exists():
        raise BundleExistsError(f"run bundle already exists: {directory}")
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=directory.parent, prefix=f".{directory.name}.tmp-"))
    try:
        records = _write_staging(staging, case_rows, artifacts or {})
        manifest_bytes = canonical_json(
            build_manifest(
                run_id=spec.run_id,
                kind=spec.kind,
                input_fingerprints=spec.input_fingerprints,
                configuration=spec.configuration,
                metrics=spec.metrics,
                verdict=spec.verdict,
                artifacts={name: (record.sha256, record.bytes) for name, record in records.items()},
            )
        )
        write_payload(staging / MANIFEST_NAME, manifest_bytes)
        fingerprint = verify_run_bundle(staging)
        exclusive_publish(staging, directory)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    _LOG.debug("published run bundle %s fingerprint=%s", directory, fingerprint)
    return PublishedBundle(directory, directory / MANIFEST_NAME, fingerprint)


def verify_run_bundle(directory: Path) -> str:
    """Refuse a missing, escaped, corrupt, or unregistered file in a published bundle.

    Artifact bytes are hashed in bounded chunks. The manifest is capped and must
    match its canonical encoding. Returns the SHA-256 fingerprint of that manifest.
    """
    root = _bundle_root(directory)
    files, directories = list_bundle_tree(root)
    if MANIFEST_NAME not in files:
        raise BundleIntegrityError("run-bundle files do not match manifest: ['manifest.json']")
    raw = _read_manifest(root)
    payload, fingerprint = load_manifest(raw)
    artifacts = artifact_records(payload)
    expected = expected_files(artifacts)
    unexpected = files ^ expected
    extra_dirs = directories - parent_directories(expected)
    if unexpected or extra_dirs:
        raise BundleIntegrityError(
            f"run-bundle files do not match manifest: {sorted(unexpected | extra_dirs)}"
        )
    for name, record in artifacts.items():
        _verify_artifact(root, name, record)
    return fingerprint


def _bundle_root(directory: Path) -> Path:
    path = Path(directory)
    if not path.exists() or not path.is_dir():
        raise BundleIntegrityError(f"run bundle is not a directory: {path}")
    return path.resolve()


def _read_manifest(root: Path) -> bytes:
    with open_contained_file(root, PurePosixPath(MANIFEST_NAME)) as fd:
        return read_capped(fd, MANIFEST_MAX_BYTES, label=MANIFEST_NAME)


def _verify_artifact(root: Path, name: str, record: Mapping[str, int | str]) -> None:
    with open_contained_file(root, artifact_path(name)) as fd:
        digest, size = digest_fd(fd)
    if record.get("bytes") != size or record.get("sha256") != digest:
        raise BundleIntegrityError(f"run-bundle artifact failed verification: {name}")


def _write_staging(
    staging: Path,
    case_rows: Sequence[Mapping[str, object]],
    artifacts: Mapping[str, str | bytes],
) -> dict[str, ArtifactRecord]:
    records = {SCORES_NAME: _write_scores(staging, case_rows)}
    for raw_name, content in artifacts.items():
        name = extra_artifact_name(raw_name)
        if name in records:
            raise BundleIntegrityError(f"duplicate bundle artifact name: {name!r}")
        payload = content.encode() if isinstance(content, str) else content
        records[name] = _stored(staging.joinpath(*PurePosixPath(name).parts), payload)
    return records


def _write_scores(staging: Path, case_rows: Sequence[Mapping[str, object]]) -> ArtifactRecord:
    hasher = hashlib.sha256()
    total = 0
    path = staging / SCORES_NAME
    with path.open("wb") as handle:
        for row in case_rows:
            line = json_line(dict(row))
            handle.write(line)
            hasher.update(line)
            total += len(line)
        handle.flush()
    return ArtifactRecord(hasher.hexdigest(), total)


def _stored(path: Path, payload: bytes) -> ArtifactRecord:
    digest, size = write_payload(path, payload)
    return ArtifactRecord(digest, size)

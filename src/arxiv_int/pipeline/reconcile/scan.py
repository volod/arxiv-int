"""Build complete comparable source manifests without modifying archive bytes."""

import hashlib
import logging
from dataclasses import replace
from pathlib import Path
from uuid import uuid4

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.reconcile.model import SiloScan, SourceManifest, SourceOccurrence
from arxiv_int.pipeline.run.context import RunContext

_LOG = logging.getLogger(__name__)
_EMPTY_SHARD = "default"


def scan_silos(
    silos: tuple[SiloRoot, ...],
    *,
    scan_id: str | None = None,
) -> SourceManifest:
    """Hash readable files; mark unavailable or unstable silos incomplete."""
    scans = tuple(_scan_one(silo) for silo in silos)
    comparable = bool(scans) and all(item.complete and item.readable for item in scans)
    manifest = SourceManifest(scan_id or f"scan-{uuid4().hex}", scans, comparable)
    if not comparable:
        _LOG.info("source scan is not comparable; removal tombstones are withheld")
    return manifest


def content_hashes(manifest: SourceManifest) -> tuple[str, ...]:
    """Return stable shard ids for complete, readable occurrences."""
    hashes = {
        item.content_hash
        for silo in manifest.silos
        for item in silo.occurrences
        if item.readable and item.stable and item.content_hash
    }
    return tuple(sorted(hashes))


def source_shard_ids(
    context: RunContext, manifest: SourceManifest | None = None
) -> tuple[str, ...]:
    """Prefer an explicit document id, else one shard per content hash."""
    document_id = context.parameters.get("document_id")
    if document_id:
        return (document_id,)
    scanned = manifest if manifest is not None else scan_silos(context.silos)
    hashes = content_hashes(scanned)
    return hashes if hashes else (_EMPTY_SHARD,)


def bind_shard(context: RunContext, shard_id: str) -> RunContext:
    """Freeze one content-hash shard into run parameters."""
    parameters = dict(context.parameters)
    parameters["document_id"] = shard_id
    return replace(context, parameters=parameters)


def _scan_one(silo: SiloRoot) -> SiloScan:
    root = silo.root
    if not root.exists() or not root.is_dir():
        return SiloScan(silo.silo_id, False, False, (), "silo missing or unreadable")
    try:
        files = tuple(_iter_files(root))
    except OSError:
        return SiloScan(silo.silo_id, False, False, (), "directory listing failed")
    occurrences: list[SourceOccurrence] = []
    complete = True
    for path in files:
        item = _read_occurrence(silo.silo_id, root, path)
        occurrences.append(item)
        if not item.readable or not item.stable:
            complete = False
    return SiloScan(silo.silo_id, complete, True, tuple(occurrences), "" if complete else "partial")


def _read_occurrence(silo_id: str, root: Path, path: Path) -> SourceOccurrence:
    relative = path.relative_to(root).as_posix()
    try:
        first = path.stat()
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        second = path.stat()
    except OSError:
        return SourceOccurrence(silo_id, relative, "unreadable", False, False)
    stable = first.st_size == second.st_size and first.st_mtime_ns == second.st_mtime_ns
    return SourceOccurrence(silo_id, relative, digest, stable, True)


def _iter_files(root: Path) -> tuple[Path, ...]:
    found: list[Path] = []
    for path in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if path.is_symlink() or not path.is_file():
            continue
        found.append(path)
    return tuple(found)

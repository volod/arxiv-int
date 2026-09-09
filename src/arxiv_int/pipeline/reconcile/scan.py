"""Build complete comparable source manifests without modifying archive bytes."""

import logging
from dataclasses import replace
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from arxiv_int.pipeline.inventory.walk import Entry

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
    if context.profile != "fixture":
        # Inventory is one source-set scan; its fixed buckets are internal partitions.
        return ("default",)
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
    from arxiv_int.pipeline.inventory.walk import walk

    occurrences: list[SourceOccurrence] = []
    readable = silo.root.is_dir()
    for entry in walk(silo.root):
        if entry.relative_path == ".":
            readable = False
            continue
        occurrences.append(_read_entry(silo, entry))
    complete = readable and all(item.readable and item.stable for item in occurrences)
    return SiloScan(
        silo.silo_id, complete, readable, tuple(occurrences), "" if complete else "partial"
    )


def _read_entry(silo: SiloRoot, entry: "Entry") -> SourceOccurrence:
    from arxiv_int.pipeline.inventory.model import InventoryPolicy
    from arxiv_int.pipeline.inventory.read import observe

    unreadable = SourceOccurrence(silo.silo_id, entry.relative_path, "unreadable", False, False)
    if entry.status != "file":
        return unreadable
    try:
        digest = "unreadable"
        for item in observe(silo.root, silo.silo_id, entry, InventoryPolicy()):
            if not item.members:
                digest = item.content_hash or "unreadable"
        return SourceOccurrence(silo.silo_id, entry.relative_path, digest, True, True)
    except OSError:
        return unreadable

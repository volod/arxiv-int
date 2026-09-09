"""Strong hashing and stability checks for physical source files."""

import hashlib
import os
import stat
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path
from typing import BinaryIO

from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.inventory.archives import Budget, members
from arxiv_int.pipeline.inventory.detect import detect
from arxiv_int.pipeline.inventory.model import InventoryPolicy, Observation
from arxiv_int.pipeline.inventory.probe import ContentProbe, quarantine_reason
from arxiv_int.pipeline.inventory.walk import Entry, open_source, signature


class UnstableSourceError(OSError):
    """Observed bytes no longer match the discovered source entry."""


def observe(
    root: Path, silo: str, entry: Entry, policy: InventoryPolicy, scratch: Path | None = None
) -> Iterator[Observation]:
    """Yield observations; a later stability failure must roll back the whole file transaction."""
    item = Observation(silo, entry.relative_path)
    if entry.status != "file":
        yield replace(item, status="quarantined", reason=entry.status)
        return
    with os.fdopen(open_source(root, entry.relative_path), "rb") as handle:
        first = os.fstat(handle.fileno())
        if not stat.S_ISREG(first.st_mode) or signature(first) != entry.signature:
            raise UnstableSourceError("source changed before open")
        measured = _hash(handle, item, policy)
        yield measured
        yield from members(handle, measured, policy, Budget(scratch=scratch))
        with os.fdopen(open_source(root, entry.relative_path), "rb") as current:
            if (
                signature(os.fstat(current.fileno())) != entry.signature
                or signature(os.fstat(handle.fileno())) != entry.signature
                or measured.size != first.st_size
            ):
                raise UnstableSourceError("source changed during read")


def _hash(handle: BinaryIO, item: Observation, policy: InventoryPolicy) -> Observation:
    digest = hashlib.sha256()
    size = 0
    probe = ContentProbe(policy.sample_bytes)
    expected = os.fstat(handle.fileno()).st_size
    while chunk := handle.read(min(policy.read_bytes, expected - size + 1)):
        check_cancelled()
        if size + len(chunk) > expected:
            raise UnstableSourceError("source grew during read")
        probe.add(chunk)
        digest.update(chunk)
        size += len(chunk)
    mime, encoding = detect(probe.sample, item.relative_path)
    reason = quarantine_reason(mime, probe.encrypted)
    return replace(
        item,
        content_hash=digest.hexdigest(),
        size=size,
        mime=mime,
        encoding=encoding,
        status="quarantined" if reason else "ready",
        reason=reason,
    )

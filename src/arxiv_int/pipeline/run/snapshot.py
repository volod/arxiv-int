"""Chunked source identities and versioned, content-free drift checks."""

import hashlib
from collections.abc import Iterable, Iterator
from pathlib import Path

from arxiv_int.contracts.generate.normalize import normalize_json, normalize_text
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.run.errors import StaleUpstreamError

CONTENT_POLICY = "full-content-v1"
METADATA_POLICY = "stat-v1"


def snapshot_silos(silos: tuple[SiloRoot, ...]) -> str:
    """Hash the original ordered path/content identity with bounded file reads."""
    return _digest_parts(_content_parts(silos))


def metadata_snapshot(silos: tuple[SiloRoot, ...]) -> str:
    """Hash stat-v1 fields without opening source files; atime is excluded."""
    return _digest_parts(_metadata_parts(silos))


def capture_snapshot(silos: tuple[SiloRoot, ...]) -> tuple[str, str]:
    """Freeze content and metadata together, refusing observed changes during hashing."""
    before = metadata_snapshot(silos)
    content = snapshot_silos(silos)
    after = metadata_snapshot(silos)
    if before != after:
        raise StaleUpstreamError("archive snapshot changed during hashing; retry on stable sources")
    return content, after


def _entries(silos: tuple[SiloRoot, ...]) -> Iterator[tuple[str, Path | None]]:
    for silo in silos:
        if not silo.root.exists():
            yield f"{silo.silo_id}:missing", None
            continue
        for path in sorted(silo.root.rglob("*")):
            if path.is_file() and not path.is_symlink():
                yield f"{silo.silo_id}:{path.relative_to(silo.root).as_posix()}", path


def _content_parts(silos: tuple[SiloRoot, ...]) -> Iterator[str]:
    for identity, path in _entries(silos):
        yield identity if path is None else f"{identity}:{hash_file(path)[0]}"


def _metadata_parts(silos: tuple[SiloRoot, ...]) -> Iterator[str]:
    for identity, path in _entries(silos):
        if path is None:
            yield normalize_json([identity])
            continue
        info = path.stat()
        yield normalize_json(
            [
                identity,
                info.st_dev,
                info.st_ino,
                info.st_size,
                info.st_mtime_ns,
                info.st_ctime_ns,
                info.st_mode,
                info.st_uid,
                info.st_gid,
            ]
        )


def _digest_parts(parts: Iterable[str]) -> str:
    hasher = hashlib.sha256()
    empty = True
    for part in parts:
        hasher.update(normalize_text(part).encode("utf-8"))
        empty = False
    if empty:
        hasher.update(b"empty-archive\n")
    return hasher.hexdigest()

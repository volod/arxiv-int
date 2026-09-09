"""Bounded ZIP and streaming TAR member inventory without extraction to source paths."""

import gzip
import hashlib
import io
import json
import stat
import struct
import tarfile
import tempfile
import zipfile
import zlib
from collections.abc import Iterator
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import IO, Any, cast

from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.inventory.detect import detect
from arxiv_int.pipeline.inventory.model import InventoryPolicy, Observation
from arxiv_int.pipeline.inventory.probe import ContentProbe, quarantine_reason
from arxiv_int.pipeline.run.errors import InterruptedPipelineError


class ArchiveLimitError(ValueError):
    """A container cannot be enumerated within the declared budget."""


@dataclass(slots=True)
class Budget:
    """Shared by every descendant of one physical file."""

    members: int = 0
    expanded: int = 0
    scratch: Path | None = None


def members(
    handle: IO[bytes], parent: Observation, policy: InventoryPolicy, budget: Budget | None = None
) -> Iterator[Observation]:
    """Inspect nested container identities; retain an explicit refusal row on failure."""
    if parent.mime not in {"application/zip", "application/x-tar", "application/gzip"}:
        return
    if len(parent.members) >= policy.archive_depth:
        yield replace(
            parent,
            members=(*parent.members, "!policy"),
            content_hash=None,
            status="quarantined",
            reason="archive-depth-limit",
        )
        return
    used = budget or Budget()
    try:
        handle.seek(0)
        if parent.mime == "application/zip":
            yield from _zip(handle, parent, policy, used)
        else:
            yield from _tar(handle, parent, policy, used)
    except InterruptedPipelineError:
        raise
    except (
        OSError,
        ValueError,
        RuntimeError,
        EOFError,
        tarfile.TarError,
        zipfile.BadZipFile,
        zlib.error,
    ):
        yield replace(
            parent,
            members=(*parent.members, "!policy"),
            content_hash=None,
            status="quarantined",
            reason="archive-invalid-or-limit",
        )


def _zip_guard(handle: IO[bytes], policy: InventoryPolicy) -> None:
    handle.seek(0, io.SEEK_END)
    length = handle.tell()
    handle.seek(max(0, length - 65_557))
    tail = handle.read(65_557)
    offset = tail.rfind(b"PK\x05\x06")
    if offset < 0 or len(tail) - offset < 22:
        raise ArchiveLimitError("missing ZIP directory")
    _sig, disk, start, count_disk, count, size, _pos, comment = struct.unpack_from(
        "<4s4H2IH", tail, offset
    )
    if (
        disk
        or start
        or count_disk != count
        or count == 65535
        or size == 0xFFFFFFFF
        or count > policy.archive_members
        or size > policy.central_directory_bytes
        or offset + 22 + comment != len(tail)
    ):
        raise ArchiveLimitError("ZIP directory budget or unsupported ZIP64/multidisk")
    handle.seek(0)


def _member(parent: Observation, name: str, index: int, size: int) -> Observation:
    # JSON keeps duplicate names, delimiters and nested paths unambiguous.
    address = json.dumps([index, name], ensure_ascii=True)
    return Observation(
        parent.silo_id,
        parent.relative_path,
        (*parent.members, address),
        size=size,
        parent_hash=parent.content_hash,
    )


def _unsafe(name: str) -> bool:
    path = PurePosixPath(name.replace("\\", "/"))
    return path.is_absolute() or ".." in path.parts or not path.parts or ":" in path.parts[0]


def _reserve(size: int, policy: InventoryPolicy, budget: Budget) -> None:
    budget.members += 1
    if (
        budget.members > policy.archive_members
        or size > policy.member_bytes
        or budget.expanded + size > policy.expanded_bytes
    ):
        raise ArchiveLimitError("archive expansion budget")


def _zip(
    handle: IO[bytes], parent: Observation, policy: InventoryPolicy, budget: Budget
) -> Iterator[Observation]:
    _zip_guard(handle, policy)
    with zipfile.ZipFile(handle) as archive:
        for index, info in enumerate(archive.infolist()):
            check_cancelled()
            _reserve(info.file_size, policy, budget)
            if info.is_dir():
                continue
            item = _member(parent, info.filename, index, info.file_size)
            reason = _zip_reason(info, policy)
            if reason:
                yield replace(item, status="quarantined", reason=reason)
                continue
            with archive.open(info) as stream:
                yield from _read_member(stream, item, policy, budget)


def _zip_reason(info: zipfile.ZipInfo, policy: InventoryPolicy) -> str | None:
    if info.flag_bits & 1:
        return "encrypted"
    if _unsafe(info.filename):
        return "unsafe-member-path"
    if stat.S_ISLNK(info.external_attr >> 16):
        return "link"
    if info.file_size > max(1, info.compress_size) * policy.expansion_ratio:
        return "expansion-ratio-limit"
    if info.compress_type not in {zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED}:
        return "unsupported-compression"
    return None


def _tar(
    handle: IO[bytes], parent: Observation, policy: InventoryPolicy, budget: Budget
) -> Iterator[Observation]:
    # stream=True suppresses retained member headers (Python 3.13+); clearing below supports 3.12.
    stream = gzip.GzipFile(fileobj=handle) if parent.mime == "application/gzip" else handle
    limit = min(policy.expanded_bytes, max(parent.size, 1) * policy.expansion_ratio)
    limited = LimitedReader(cast(IO[bytes], stream), limit)
    with tarfile.open(fileobj=cast(IO[bytes], limited), mode="r|") as archive:
        for index, info in enumerate(archive):
            check_cancelled()
            cast(Any, archive).members.clear()
            _reserve(info.size, policy, budget)
            item = _member(parent, info.name, index, info.size)
            if info.isdir():
                continue
            if not info.isfile() or _unsafe(info.name):
                yield replace(item, status="quarantined", reason="link-or-unsafe-member")
                continue
            member_stream = archive.extractfile(info)
            if member_stream is None:
                raise ArchiveLimitError("unreadable TAR member")
            with member_stream:
                yield from _read_member(member_stream, item, policy, budget)


def _read_member(
    stream: IO[bytes], item: Observation, policy: InventoryPolicy, budget: Budget
) -> Iterator[Observation]:
    digest = hashlib.sha256()
    size = 0
    probe = ContentProbe(policy.sample_bytes)
    with tempfile.SpooledTemporaryFile(
        max_size=policy.sample_bytes,
        dir=str(budget.scratch) if budget.scratch is not None else None,
    ) as nested:
        while chunk := stream.read(min(policy.read_bytes, policy.member_bytes - size + 1)):
            check_cancelled()
            size += len(chunk)
            budget.expanded += len(chunk)
            if size > policy.member_bytes or budget.expanded > policy.expanded_bytes:
                raise ArchiveLimitError("actual expansion budget")
            digest.update(chunk)
            probe.add(chunk)
            nested.write(chunk)
        if size != item.size:
            raise ArchiveLimitError("member size mismatch")
        mime, encoding = detect(probe.sample, str(json.loads(item.members[-1])[1]))
        reason = quarantine_reason(mime, probe.encrypted)
        measured = replace(
            item,
            content_hash=digest.hexdigest(),
            size=size,
            mime=mime,
            encoding=encoding,
            status="quarantined" if reason else "ready",
            reason=reason,
        )
        yield measured
        yield from members(nested, measured, policy, budget)


class LimitedReader:
    """Bound decompressed TAR headers as well as regular member bodies."""

    def __init__(self, stream: IO[bytes], limit: int) -> None:
        self.stream = stream
        self.remaining = limit

    def read(self, size: int = -1) -> bytes:
        check_cancelled()
        if size < 0 or size > self.remaining:
            raise ArchiveLimitError("TAR stream budget")
        payload = self.stream.read(size)
        self.remaining -= len(payload)
        return payload

"""Read validated inventory observations and materialize safe scratch copies."""

import gzip
import hashlib
import io
import json
import os
import tarfile
import tempfile
import zipfile
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path, PurePosixPath
from typing import IO, Any, cast

from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy, InventoryInput
from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.inventory.publish import validate_manifest
from arxiv_int.pipeline.inventory.stage import inventory_root


def inventory_inputs(context: StageContext) -> Iterator[InventoryInput]:
    """Yield one generation's observations after validating all referenced checksums."""
    referenced = context.options.get("inventory_manifest", "")
    if referenced:
        manifest = Path(referenced)
        expected_digest = context.options.get("inventory_manifest_sha256", "")
        if not expected_digest:
            raise ValueError("inventory manifest reference has no checksum")
    else:
        root = inventory_root(context)
        manifests = sorted(root.glob("snapshot=*/inventory.json"))
        if not manifests:
            raise ValueError("extract requires a published inventory snapshot")
        manifest = manifests[-1]
        expected_digest = _sha256(manifest)
    summary = validate_manifest(manifest, expected_digest)
    if not referenced and summary["generation_id"] != context.generation_id:
        raise ValueError("inventory generation does not match extraction generation")
    with (manifest.parent / "partitions.jsonl").open(encoding="ascii") as index:
        for line in index:
            partition = json.loads(line)
            with (manifest.parent / partition["metadata"]).open(encoding="ascii") as metadata:
                for row in metadata:
                    yield _input(json.loads(row))


@contextmanager
def materialized_source(
    context: StageContext,
    item: InventoryInput,
    policy: ExtractionPolicy,
    scratch: Path,
) -> Iterator[Path]:
    """Copy verified physical or member bytes to bounded, tool-only scratch."""
    source = context.silo_root(item.silo_id) / item.relative_path
    before = source.stat(follow_symlinks=False)
    if not source.is_file() or source.is_symlink():
        raise ExtractionError("source-unavailable", "inventory source is not a regular file")
    payload = _read_limited(source, policy.input_bytes)
    after = source.stat(follow_symlinks=False)
    if _signature(before) != _signature(after):
        raise ExtractionError("source-changed", "source changed while preparing extraction")
    if item.members:
        payload = _member_payload(payload, item.members, policy.input_bytes)
    digest = hashlib.sha256(payload).hexdigest()
    if item.content_hash is None or digest != item.content_hash:
        raise ExtractionError(
            "content-hash-mismatch", "source bytes differ from inventory identity"
        )
    suffix = _suffix(item)
    scratch.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(suffix=suffix, dir=scratch)
    staged = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        yield staged
    finally:
        staged.unlink(missing_ok=True)


def _input(value: dict[str, Any]) -> InventoryInput:
    return InventoryInput(
        occurrence_id=str(value["occurrence_id"]),
        silo_id=str(value["silo_id"]),
        relative_path=str(value["relative_path"]),
        members=tuple(str(item) for item in value.get("members", [])),
        content_hash=value.get("content_hash"),
        size=int(value.get("size", 0)),
        media_type=str(value.get("mime", "application/octet-stream")),
        encoding=value.get("encoding"),
        status=str(value.get("status", "quarantined")),
        reason=value.get("reason"),
    )


def _read_limited(path: Path, limit: int) -> bytes:
    with path.open("rb") as handle:
        payload = handle.read(limit + 1)
    if len(payload) > limit:
        raise ExtractionError(
            "input-size-limit", f"source exceeds extraction limit of {limit} bytes"
        )
    return payload


def _member_payload(payload: bytes, addresses: tuple[str, ...], limit: int) -> bytes:
    current = payload
    for encoded in addresses:
        try:
            index, name = json.loads(encoded)
        except (TypeError, ValueError, json.JSONDecodeError) as error:
            raise ExtractionError(
                "invalid-member-address", "inventory member address is invalid"
            ) from error
        if not isinstance(index, int) or not isinstance(name, str):
            raise ExtractionError("invalid-member-address", "inventory member address is invalid")
        current = _one_member(current, index, name, limit)
    return current


def _one_member(payload: bytes, index: int, name: str, limit: int) -> bytes:
    try:
        if payload.startswith((b"PK\x03\x04", b"PK\x05\x06")):
            return _zip_member(payload, index, name, limit)
        return _tar_member(payload, index, name, limit)
    except ExtractionError:
        raise
    except (OSError, ValueError, tarfile.TarError, zipfile.BadZipFile) as error:
        raise ExtractionError("member-unreadable", "cannot reopen inventory member") from error


def _zip_member(payload: bytes, index: int, name: str, limit: int) -> bytes:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        entries = archive.infolist()
        if index >= len(entries) or entries[index].filename != name:
            raise ExtractionError("member-changed", "ZIP member identity changed")
        with archive.open(entries[index]) as member_stream:
            return _stream_limited(member_stream, limit)


def _tar_member(payload: bytes, index: int, name: str, limit: int) -> bytes:
    stream: IO[bytes]
    if payload.startswith(b"\x1f\x8b"):
        stream = cast(IO[bytes], gzip.GzipFile(fileobj=io.BytesIO(payload)))
    else:
        stream = io.BytesIO(payload)
    with tarfile.open(fileobj=stream, mode="r|") as archive:
        for ordinal, info in enumerate(archive):
            if ordinal != index:
                continue
            if info.name != name or not info.isfile():
                raise ExtractionError("member-changed", "TAR member identity changed")
            member = archive.extractfile(info)
            if member is not None:
                with member:
                    return _stream_limited(member, limit)
    raise ExtractionError("member-changed", "inventory member is no longer present")


def _stream_limited(stream: IO[bytes], limit: int) -> bytes:
    payload = stream.read(limit + 1)
    if len(payload) > limit:
        raise ExtractionError(
            "input-size-limit", f"member exceeds extraction limit of {limit} bytes"
        )
    return payload


def _suffix(item: InventoryInput) -> str:
    name = item.relative_path
    if item.members:
        with suppress(TypeError, ValueError, json.JSONDecodeError, IndexError):
            name = str(json.loads(item.members[-1])[1])
    return PurePosixPath(name).suffix[:16]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _signature(value: os.stat_result) -> tuple[int, int, int, int]:
    return (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)

"""Nested, encrypted, corrupt, unsafe and expansion-limited archive fixtures."""

import io
import struct
import tarfile
import zipfile
from dataclasses import replace

from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.inventory.archives import members
from arxiv_int.pipeline.inventory.model import InventoryPolicy, Observation
from tests.pipeline.inventory.conftest import run_inventory


def zip_bytes(files: list[tuple[str, bytes]], compression: int = zipfile.ZIP_STORED) -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=compression) as archive:
        for name, payload in files:
            archive.writestr(name, payload)
    return output.getvalue()


def test_nested_container_hashes_and_member_provenance(context: StageContext) -> None:
    inner = zip_bytes([("text.txt", b"member text")])
    outer = zip_bytes([("nested.zip", inner), ("../unsafe", b"secret")])
    (context.silos[0].root / "outer.zip").write_bytes(outer)
    _, rows, _ = run_inventory(context)
    assert len(rows) == 4
    deepest = next(row for row in rows if len(row["members"]) == 2)
    parent = next(row for row in rows if row["mime"] == "application/zip" and row["members"])
    assert deepest["parent_hash"] == parent["content_hash"]
    assert deepest["encoding"] == "ascii"
    assert any(row["reason"] == "unsafe-member-path" for row in rows)


def test_encryption_flag_is_quarantined_without_decryption(context: StageContext) -> None:
    payload = bytearray(zip_bytes([("encrypted.txt", b"unreadable")]))
    local = payload.index(b"PK\x03\x04")
    central = payload.index(b"PK\x01\x02")
    struct.pack_into("<H", payload, local + 6, 1)
    struct.pack_into("<H", payload, central + 8, 1)
    (context.silos[0].root / "encrypted.zip").write_bytes(payload)
    _, rows, _ = run_inventory(context)
    encrypted = next(row for row in rows if row["members"])
    assert encrypted["reason"] == "encrypted"
    assert encrypted["content_hash"] is None


def test_corrupt_zip_and_expansion_ratio_are_explicit(context: StageContext) -> None:
    root = context.silos[0].root
    (root / "corrupt.zip").write_bytes(b"PK\x03\x04broken")
    (root / "bomb.zip").write_bytes(zip_bytes([("zeros", b"0" * 1_000_000)], zipfile.ZIP_DEFLATED))
    _, rows, _ = run_inventory(context)
    reasons = {row["reason"] for row in rows}
    assert {"archive-invalid-or-limit", "expansion-ratio-limit"} <= reasons


def test_tar_members_stream_and_links_are_not_followed(context: StageContext) -> None:
    path = context.silos[0].root / "container.tar"
    with tarfile.open(path, "w") as archive:
        info = tarfile.TarInfo("text")
        info.size = 4
        archive.addfile(info, io.BytesIO(b"text"))
        link = tarfile.TarInfo("link")
        link.type = tarfile.SYMTYPE
        link.linkname = "/outside"
        archive.addfile(link)
    _, rows, _ = run_inventory(context)
    assert len(rows) == 3
    assert any(row["reason"] == "link-or-unsafe-member" for row in rows)


def test_archive_member_depth_and_byte_limits() -> None:
    parent = Observation("one", "archive", content_hash="a" * 64, mime="application/zip")
    payload = zip_bytes([("a", b"a"), ("b", b"b")])
    rows = list(members(io.BytesIO(payload), parent, InventoryPolicy(archive_members=1)))
    assert rows[0].reason == "archive-invalid-or-limit"
    rows = list(
        members(
            io.BytesIO(payload),
            replace(parent, members=("nested",)),
            InventoryPolicy(archive_depth=1),
        )
    )
    assert rows[0].reason == "archive-depth-limit"
    payload = zip_bytes([("large", b"123456")])
    rows = list(members(io.BytesIO(payload), parent, InventoryPolicy(member_bytes=5)))
    assert rows[0].reason == "archive-invalid-or-limit"


def test_cancellation_inside_archive_is_not_quarantined() -> None:
    import pytest

    from arxiv_int.pipeline.dag.cancel import CancelToken, cancellation_scope
    from arxiv_int.pipeline.run.errors import InterruptedPipelineError

    parent = Observation("one", "archive", content_hash="a" * 64, mime="application/zip")
    token = CancelToken()
    token.cancel()
    with cancellation_scope(token), pytest.raises(InterruptedPipelineError):
        list(members(io.BytesIO(zip_bytes([("x", b"x")])), parent, InventoryPolicy()))


def test_member_format_and_pdf_encryption_policy_matches_files(context: StageContext) -> None:
    payload = zip_bytes(
        [("unknown", b"\x00binary"), ("protected.pdf", b"%PDF-1.4\n/Encrypt 1 0 R")]
    )
    (context.silos[0].root / "container.zip").write_bytes(payload)
    _, rows, _ = run_inventory(context)
    member_rows = [row for row in rows if row["members"]]
    assert {row["reason"] for row in member_rows} == {"unsupported-format", "encrypted-pdf-marker"}
    assert all(row["content_hash"] for row in member_rows)

"""Content identities, source coverage and validated immutable artifacts."""

import hashlib
import os
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.inventory.checkpoint import Checkpoint
from arxiv_int.pipeline.inventory.model import Observation
from arxiv_int.pipeline.inventory.publish import validate_manifest
from arxiv_int.pipeline.inventory.validate import InventoryValidator
from tests.pipeline.inventory.conftest import run_inventory


def test_two_silos_duplicates_and_atomic_partitions(context: StageContext, tmp_path: Path) -> None:
    (context.silos[0].root / "same.txt").write_bytes(b"same bytes")
    (context.silos[0].root / "renamed.txt").write_bytes(b"same bytes")
    second = tmp_path / "second"
    second.mkdir()
    (second / "same.txt").write_bytes(b"same bytes")
    scoped = replace(context, silos=(*context.silos, SiloRoot("two", second)))
    summary, rows, manifest = run_inventory(scoped)
    assert len(rows) == 3
    assert len({row["occurrence_id"] for row in rows}) == 3
    assert {row["content_hash"] for row in rows} == {hashlib.sha256(b"same bytes").hexdigest()}
    assert summary["silos"]["one"]["duplicates"] == 1
    assert summary["completed_source_set"] == {"one": True, "two": True}
    assert summary["pandera"]["checked_rows"] == 3
    digest = hashlib.sha256(manifest.read_bytes()).hexdigest()
    assert validate_manifest(manifest, digest)["global_occurrence_keys"]["status"] == "pass"
    next(manifest.parent.glob("*.parquet")).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="checksum"):
        validate_manifest(manifest, digest)


def test_links_specials_and_missing_scope(context: StageContext) -> None:
    root = context.silos[0].root
    (root / "broken").symlink_to(root / "absent")
    (root / "cycle").symlink_to(root, target_is_directory=True)
    os.mkfifo(root / "fifo")
    summary, rows, _ = run_inventory(context)
    assert sorted(row["reason"] for row in rows) == ["link", "link", "unsupported-special"]
    assert summary["silos"]["one"]["quarantined"] == 3
    missing = replace(
        context, generation_id="missing", silos=(SiloRoot("missing", root / "absent"),)
    )
    summary, rows, _ = run_inventory(missing)
    assert summary["completed_source_set"] == {"missing": False}
    assert rows[0]["reason"] == "unreadable-directory"


def test_empty_inventory_records_completed_global_check(context: StageContext) -> None:
    summary, rows, _ = run_inventory(context)
    assert rows == []
    assert summary["global_occurrence_keys"]["checked_rows"] == 0
    assert summary["completed_source_set"] == {"one": True}


def test_invalid_provenance_and_global_duplicate_refuse(tmp_path: Path) -> None:
    validator = InventoryValidator(Path.cwd())
    item = Observation("unknown", "../outside", content_hash="invalid")
    with pytest.raises(ValueError, match="provenance"):
        validator.batch([item], "scan", "generation", frozenset({"one"}))
    checkpoint = Checkpoint(tmp_path / "state.sqlite", "fixture")
    try:
        checkpoint.add(Observation("one", "same"))
        with pytest.raises(sqlite3.IntegrityError):
            checkpoint.add(Observation("one", "same"))
    finally:
        checkpoint.close()


def test_output_symlink_cannot_write_to_source(context: StageContext) -> None:
    context.results_dir.mkdir()
    (context.results_dir / "normalized").symlink_to(context.silos[0].root, target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        run_inventory(context)
    assert list(context.silos[0].root.iterdir()) == []


def test_archive_scratch_honors_context_and_protects_sources(
    context: StageContext, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import tempfile
    import zipfile

    from arxiv_int.pipeline.inventory import archives

    with zipfile.ZipFile(context.silos[0].root / "container.zip", "w") as archive:
        archive.writestr("member", b"bounded scratch")
    scratch = tmp_path / "configured-scratch"
    original = tempfile.SpooledTemporaryFile
    seen = []

    def spool(*args: object, **kwargs: object):
        seen.append(kwargs.get("dir"))
        return original(*args, **kwargs)

    monkeypatch.setattr(archives.tempfile, "SpooledTemporaryFile", spool)
    scoped = replace(context, options={**context.options, "tmp_dir": str(scratch)})
    run_inventory(scoped)
    assert seen == [str(scratch)]
    assert list(scratch.iterdir()) == []
    scoped = replace(context, options={**context.options, "tmp_dir": str(context.silos[0].root)})
    with pytest.raises(ValueError, match="protected"):
        run_inventory(scoped)

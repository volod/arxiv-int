"""Bounded sampling, inventory manifests, and schema drift."""

from pathlib import Path

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.forecast.sample import resolve_inventory, sample_silos
from arxiv_int.pipeline.forecast.schema import check_schema_drift
from arxiv_int.pipeline.run.persist import write_json


def test_metadata_sampling_does_not_read_file_contents(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "a.txt").write_text("hello", encoding="utf-8")
    (archive / "b.pdf").write_bytes(b"%PDF-1.4")
    nested = archive / "nested"
    nested.mkdir()
    (nested / "c.txt").write_text("more", encoding="utf-8")
    evidence = sample_silos((SiloRoot("default", archive),), file_limit=10)
    assert evidence.files == 3
    assert evidence.bytes > 0
    assert evidence.source == "sample"
    assert evidence.formats["txt"][0] == 2
    assert evidence.formats["pdf"][0] == 1
    assert not evidence.truncated


def test_sample_limit_marks_truncated(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    for index in range(5):
        (archive / f"{index}.txt").write_text("x", encoding="utf-8")
    evidence = sample_silos((SiloRoot("default", archive),), file_limit=2)
    assert evidence.files == 2
    assert evidence.truncated


def test_inventory_manifest_preferred_over_sampling(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "a.txt").write_text("hello", encoding="utf-8")
    run = tmp_path / "run-1"
    write_json(
        run / "inventory" / "manifest.json",
        {
            "added": 2,
            "bytes": 99,
            "changed": 1,
            "files": 10,
            "formats": {"pdf": {"bytes": 80, "files": 8}, "txt": {"bytes": 19, "files": 2}},
            "removed": 0,
            "renamed": 0,
            "schema": "arxiv-int.inventory.v1",
        },
    )
    evidence = resolve_inventory((SiloRoot("default", archive),), (run,), file_limit=100)
    assert evidence.source == "inventory"
    assert evidence.files == 10
    assert evidence.changed == 1
    assert evidence.bytes == 99


def test_delta_manifest_preferred_over_inventory(tmp_path: Path) -> None:
    run = tmp_path / "run-1"
    write_json(run / "inventory" / "manifest.json", {"bytes": 50, "files": 5})
    write_json(
        run / "delta" / "manifest.json",
        {"added": 1, "bytes": 12, "changed": 0, "files": 2, "removed": 0, "renamed": 0},
    )
    evidence = resolve_inventory((), (run,), file_limit=100)
    assert evidence.source == "delta"
    assert evidence.files == 2
    assert evidence.added == 1


def test_capacity_schema_and_envelope_match_the_checkout() -> None:
    root = Path(__file__).resolve().parents[3]
    assert check_schema_drift(root) == ()

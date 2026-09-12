"""Integrated physical-file accounting and publication tests for ``classify``."""

import io
import json
import zipfile
from pathlib import Path

import pytest

from arxiv_int.classification.artifacts import validate_manifest
from arxiv_int.classification.model import Classification, PhysicalFile
from arxiv_int.classification.publish import ClassificationPublisher
from arxiv_int.classification.source import physical_files, source_snapshots
from arxiv_int.extraction.model import ExtractionError
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.interfaces.sources import SourceAnchor, SourceOccurrence
from tests.classification.stage_helpers import class_rows as _class_rows
from tests.classification.stage_helpers import classify as _classify
from tests.classification.stage_helpers import classify_context as _context
from tests.classification.stage_helpers import rows as _rows
from tests.pipeline.chain import run_chain


class _ArchiveRouter:
    """Extract text members but record the physical ZIP as a container-only failure."""

    def extract(
        self,
        source: Path,
        occurrence: SourceOccurrence,
        media_type: str,
        encoding: str | None,
    ) -> ExtractedDocument:
        payload = source.read_bytes()
        if payload.startswith(b"PK"):
            raise ExtractionError("container-only", "fixture ZIP has no direct text")
        text = payload.decode(encoding or "utf-8")
        anchor = SourceAnchor(occurrence, start_char=0, end_char=len(text), page=1, kind="text")
        return ExtractedDocument(text, media_type, occurrence, "fixture", (anchor,), {})


def test_stage_maps_every_physical_file_once_with_explicit_outcomes(tmp_path: Path) -> None:
    run = run_chain(
        tmp_path,
        fixtures={
            "machine-learning.txt": "Machine learning artificial intelligence data science",
            "structures.txt": "Structural engineering structural analysis and design",
            "random.txt": "xqz unrelated gibberish 193847",
            "blank.txt": "\u200b\n",
        },
    )
    result = _classify(run)
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = validate_manifest(manifest, str(result.outputs[0].partition["sha256"]))
    rows = _rows(manifest)

    assert result.outcome == "produced"
    assert summary["accounting"] == {
        "classified_rows": 4,
        "physical_inventory_rows": 4,
        "text_budget_truncated_rows": 0,
        "virtual_member_rows": 0,
    }
    assert len({row["occurrence_id"] for row in rows}) == len(rows) == 4
    by_path = {row["relative_path"]: row for row in rows}
    assert by_path["machine-learning.txt"]["primary_class_id"] == "tax:02.03.01"
    assert by_path["structures.txt"]["primary_class_id"] == "tax:04.02.01"
    assert by_path["random.txt"]["primary_class_id"] == "unclassified"
    assert by_path["blank.txt"]["primary_class_id"] == "unreadable"
    assert json.loads(str(by_path["machine-learning.txt"]["evidence_json"]))
    assert all(row["review_state"] == "proposed" for row in rows)
    packet_path = (
        run.context.results_dir / "runs/run-chain/review/classification/operating-point.json"
    )
    packet = json.loads(packet_path.read_text(encoding="ascii"))
    assert packet["mappingManifest"] == {
        "path": str(manifest),
        "sha256": result.outputs[0].partition["sha256"],
    }
    assert packet["reviewSamples"]["assigned"][0]["relativePath"] == "machine-learning.txt"
    assert {sample["primary"] for sample in packet["reviewSamples"]["exceptional"]} == {
        "unclassified",
        "unreadable",
    }
    assert packet["pending"] == ["prove-archive-classification-on-provided-archive"]


def test_independent_unchanged_runs_are_byte_logically_reproducible(tmp_path: Path) -> None:
    fixtures = {"machine-learning.txt": "Machine learning artificial intelligence data science"}
    first = run_chain(tmp_path / "first", fixtures=fixtures)
    second = run_chain(tmp_path / "second", fixtures=fixtures)

    left = _rows(Path(_classify(first).outputs[0].partition["manifest"]))
    right = _rows(Path(_classify(second).outputs[0].partition["manifest"]))

    ignored = {"extraction_fingerprint"}
    assert [{key: value for key, value in row.items() if key not in ignored} for row in left] == [
        {key: value for key, value in row.items() if key not in ignored} for row in right
    ]


def test_upstream_tampering_is_refused_before_publication(tmp_path: Path) -> None:
    run = run_chain(tmp_path, fixtures={"source.txt": "Machine learning data science"})
    normalization = run.manifest(run.normalize)
    summary = json.loads(normalization.read_text(encoding="ascii"))
    view = next((Path(str(summary["roots"]["normalized-documents"])) / "search").iterdir())
    view.write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum"):
        _classify(run)


def test_virtual_archive_member_informs_but_does_not_duplicate_container_row(
    tmp_path: Path,
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("paper.txt", "Machine learning artificial intelligence and data science")
    run = run_chain(
        tmp_path,
        fixtures={},
        raw_fixtures={"bundle.zip": buffer.getvalue()},
        router=_ArchiveRouter(),
    )

    result = _classify(run)
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = validate_manifest(manifest, str(result.outputs[0].partition["sha256"]))
    rows = _rows(manifest)

    assert summary["accounting"]["physical_inventory_rows"] == 1
    assert summary["accounting"]["virtual_member_rows"] >= 1
    assert len(rows) == 1
    assert rows[0]["relative_path"] == "bundle.zip"
    assert rows[0]["primary_class_id"] == "tax:02.03.01"


def test_interruption_leaves_no_sealed_mapping_and_a_retry_succeeds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run = run_chain(
        tmp_path,
        fixtures={
            "one.txt": "Machine learning artificial intelligence data science",
            "two.txt": "Structural engineering structural analysis and design",
        },
    )
    original = ClassificationPublisher.add
    calls = 0

    def interrupt(
        publisher: ClassificationPublisher, item: PhysicalFile, classification: Classification
    ) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        original(publisher, item, classification)

    monkeypatch.setattr(ClassificationPublisher, "add", interrupt)
    with pytest.raises(KeyboardInterrupt):
        _classify(run)
    assert not list((run.context.results_dir / "normalized/classification").rglob("classify.json"))

    monkeypatch.setattr(ClassificationPublisher, "add", original)
    assert _classify(run).outcome == "produced"


def test_text_budget_truncation_is_reported_not_silently_dropped(tmp_path: Path) -> None:
    run = run_chain(
        tmp_path,
        fixtures={"long.txt": "Machine learning artificial intelligence and data science " * 40},
    )
    snapshots = source_snapshots(_context(run))

    generous = next(physical_files(snapshots, max_text_chars=100_000))
    clipped = next(physical_files(snapshots, max_text_chars=12))

    assert generous.truncated_document_ids == ()
    assert clipped.truncated_document_ids == tuple(item.document_id for item in generous.documents)


def test_review_packet_names_the_upstream_chain_and_its_denominators(tmp_path: Path) -> None:
    run = run_chain(
        tmp_path,
        fixtures={
            "machine-learning.txt": "Machine learning artificial intelligence data science",
            "blank.txt": "​\n",
        },
    )
    result = _classify(run)
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = validate_manifest(manifest, str(result.outputs[0].partition["sha256"]))
    packet = json.loads(
        (
            run.context.results_dir / "runs/run-chain/review/classification/operating-point.json"
        ).read_text(encoding="ascii")
    )

    assert packet["upstream"] == summary["upstream"]
    assert set(packet["upstream"]) == {"inventory", "extraction", "normalization"}
    assert all({"manifest", "sha256"} == set(value) for value in packet["upstream"].values())
    assert packet["accounting"] == summary["accounting"]
    assert packet["accounting"]["classified_rows"] == sum(packet["countsByPrimary"].values())
    assert packet["accounting"]["text_budget_truncated_rows"] == 0
    assert packet["scheme"] == summary["scheme"]


def test_every_assigned_class_and_ancestor_resolves_to_a_published_scheme_row(
    tmp_path: Path,
) -> None:
    run = run_chain(
        tmp_path,
        fixtures={
            "machine-learning.txt": "Machine learning artificial intelligence data science",
            "structures.txt": "Structural engineering structural analysis and design",
            "random.txt": "xqz unrelated gibberish 193847",
            "blank.txt": "​\n",
        },
    )
    result = _classify(run)
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = validate_manifest(manifest, str(result.outputs[0].partition["sha256"]))
    scheme_id = str(summary["scheme"]["scheme_id"])
    published = {
        str(row["class_id"]): row
        for row in _class_rows(manifest)
        if str(row["scheme_id"]) == scheme_id
    }
    exceptional = {"unclassified", "unreadable"}
    rows = _rows(manifest)

    assert published and exceptional <= set(published)
    for row in rows:
        assert str(row["scheme_id"]) == scheme_id
        path = str(row["ancestor_path"]).split(">")
        assert path[-1] == str(row["primary_class_id"])
        assert set(path) <= set(published)
        alternates = json.loads(str(row["alternate_class_ids_json"]))
        assert set(alternates) <= set(published) - exceptional
        if str(row["primary_class_id"]) in exceptional:
            assert row["failure_reason"] and path == [str(row["primary_class_id"])]
        else:
            assert row["failure_reason"] is None and len(path) > 1

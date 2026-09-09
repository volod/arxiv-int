import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest

from arxiv_int.extraction.artifacts import validate_manifest
from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy, InventoryInput
from arxiv_int.extraction.router import TieredExtractor
from arxiv_int.extraction.stage import ExtractionStage, _member_path
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.interfaces.sources import BoundingBox, SiloRoot, SourceAnchor, SourceOccurrence
from arxiv_int.pipeline.inventory.stage import InventoryStage


class FixtureRouter:
    def extract(
        self,
        source: Path,
        occurrence: SourceOccurrence,
        media_type: str,
        encoding: str | None,
    ) -> ExtractedDocument:
        payload = source.read_bytes()
        if b"corrupt" in payload:
            raise ExtractionError("parser-corrupt", "fixture parser rejected corrupt content")
        if media_type == "application/pdf":
            text = "amount 100 kg"
            anchors = (
                SourceAnchor(
                    occurrence,
                    start_char=0,
                    end_char=len(text),
                    page=2,
                    row=0,
                    column=1,
                    bbox=BoundingBox(1, 2, 3, 4),
                    kind="table-cell",
                ),
            )
        elif media_type.startswith("image/"):
            text = "scanned label"
            anchors = (
                SourceAnchor(
                    occurrence,
                    start_char=0,
                    end_char=len(text),
                    page=1,
                    bbox=BoundingBox(10, 20, 30, 40),
                    kind="ocr-word",
                ),
            )
        else:
            text = payload.decode(encoding or "utf-8")
            anchors = (
                SourceAnchor(
                    occurrence,
                    start_char=0,
                    end_char=len(text),
                    page=1,
                    kind="text",
                ),
            )
        return ExtractedDocument(
            text,
            media_type,
            occurrence,
            "fixture",
            anchors,
            {"tool_version": "fixture-1"},
        )


def test_member_anchor_uses_innermost_relative_path() -> None:
    item = InventoryInput(
        "occurrence",
        "one",
        "bundle.zip",
        ('[0, "nested/report.txt"]',),
        "a" * 64,
        10,
        "text/plain",
        "utf-8",
        "ready",
        None,
    )

    assert _member_path(item) == "nested/report.txt"


@pytest.fixture
def extracted(tmp_path: Path) -> tuple[StageContext, StageResult, dict[str, str]]:
    sources = tmp_path / "sources"
    sources.mkdir()
    fixtures = {
        "one.txt": b"same text",
        "duplicate.txt": b"same text",
        "table.pdf": b"%PDF-table",
        "scan.png": b"\x89PNG\r\n\x1a\nfixture",
        "corrupt.pdf": b"%PDF-corrupt",
        "oversized.txt": b"x" * 100,
    }
    for name, payload in fixtures.items():
        (sources / name).write_bytes(payload)
    before = {name: hashlib.sha256(payload).hexdigest() for name, payload in fixtures.items()}
    context = StageContext(
        "inventory",
        "run-extract",
        "run-extract",
        (SiloRoot("one", sources),),
        tmp_path / "results",
        {"project_root": str(Path.cwd()), "tmp_dir": str(tmp_path / "scratch")},
    )
    InventoryStage().run(context)
    policy = ExtractionPolicy(input_bytes=64, batch_rows=2, spans_per_document=10)
    result = ExtractionStage(policy, cast(TieredExtractor, FixtureRouter())).run(
        replace(context, stage="extract")
    )
    return context, result, before


def test_stage_publishes_contracts_anchors_quarantine_and_dedupe(
    extracted: tuple[StageContext, object, dict[str, str]],
) -> None:
    _context, result, _before = extracted
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = json.loads(manifest.read_text(encoding="ascii"))

    assert result.outcome == "partial"
    assert summary["documents"] == 3
    assert summary["spans"] == 3
    assert summary["quarantined"] == 2
    assert summary["reused_content"] == 1
    assert summary["coverage"] == {"anchor_documents": 3, "table_documents": 1}
    assert summary["formats"]["application/pdf"] == {
        "anchored_chars": 13,
        "anchors": 1,
        "documents": 1,
        "table_cells": 1,
        "text_chars": 13,
    }
    assert {output.dataset for output in result.outputs} == {"documents", "spans"}
    assert all(validation.publishable for validation in result.validations)


def test_stage_preserves_rich_anchor_sidecars(
    extracted: tuple[StageContext, object, dict[str, str]],
) -> None:
    _context, result, _before = extracted
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = json.loads(manifest.read_text(encoding="ascii"))
    roots = {name: Path(value) for name, value in summary["roots"].items()}
    span_metadata = [
        json.loads(line)
        for path in roots["spans"].glob("*.metadata.jsonl")
        for line in path.read_text().splitlines()
    ]
    assert any(item["row"] == 0 and item["column"] == 1 for item in span_metadata)
    assert any(item["bbox"] == {"x0": 10, "x1": 30, "y0": 20, "y1": 40} for item in span_metadata)


def test_stage_preserves_occurrences_quarantine_and_sources(
    extracted: tuple[StageContext, object, dict[str, str]],
) -> None:
    context, result, before = extracted
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = json.loads(manifest.read_text(encoding="ascii"))
    roots = {name: Path(value) for name, value in summary["roots"].items()}
    occurrences = [
        json.loads(line)
        for line in (roots["documents"] / "occurrences.jsonl").read_text().splitlines()
    ]
    assert sum(item["reused_content"] for item in occurrences) == 1
    reasons = {
        item["reason"]
        for item in (
            json.loads(line)
            for line in (roots["quarantine"] / "quarantine.jsonl").read_text().splitlines()
        )
    }
    assert reasons == {"input-size-limit", "parser-corrupt"}
    assert validate_manifest(manifest, hashlib.sha256(manifest.read_bytes()).hexdigest()) == summary
    assert {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in context.silos[0].root.iterdir()
    } == before


def test_manifest_rejects_corrupt_external_text(
    extracted: tuple[StageContext, object, dict[str, str]],
) -> None:
    _context, result, _before = extracted
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = json.loads(manifest.read_text(encoding="ascii"))
    text = next((Path(summary["roots"]["documents"]) / "text").iterdir())
    text.write_text("tampered", encoding="utf-8")

    with pytest.raises(ValueError, match="checksum"):
        validate_manifest(manifest, hashlib.sha256(manifest.read_bytes()).hexdigest())

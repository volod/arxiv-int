import json
from pathlib import Path

import pytest

from arxiv_int.extraction import iscc_tika
from arxiv_int.extraction.docling import _document
from arxiv_int.extraction.iscc_tika import IsccTikaExtractor
from arxiv_int.extraction.model import ExtractionPolicy
from arxiv_int.extraction.process import CommandResult
from arxiv_int.interfaces.sources import SourceOccurrence


def test_docling_json_preserves_page_table_and_bbox() -> None:
    occurrence = SourceOccurrence("one", "table.pdf", "scan")
    payload = {
        "texts": [
            {
                "text": "Heading",
                "label": "section_header",
                "prov": [{"page_no": 1, "bbox": {"l": 1, "t": 2, "r": 3, "b": 4}}],
            }
        ],
        "tables": [
            {
                "data": {
                    "table_cells": [
                        {
                            "text": "100 kg",
                            "start_row_offset_idx": 0,
                            "start_col_offset_idx": 1,
                            "prov": [{"page_no": 2, "bbox": {"l": 10, "t": 20, "r": 30, "b": 40}}],
                        }
                    ]
                }
            }
        ],
    }

    document = _document(payload, occurrence, "docling fixture", 10)

    assert document.text == "Heading\n100 kg"
    cell = document.anchors[1]
    assert (cell.page, cell.row, cell.column, cell.kind) == (2, 0, 1, "table-cell")
    assert cell.bbox is not None
    assert (cell.bbox.x0, cell.bbox.y1) == (10, 40)


def test_native_tika_binding_extracts_without_server(tmp_path: Path) -> None:
    pytest.importorskip("iscc_tika")
    source = tmp_path / "russian.txt"
    expected = "\u0414\u043e\u0433\u043e\u0432\u043e\u0440 \u043d\u043e\u043c\u0435\u0440 42"
    source.write_text(expected, encoding="utf-8")
    occurrence = SourceOccurrence("one", "russian.txt", "scan", content_hash="a" * 64)
    policy = ExtractionPolicy(timeout_seconds=30, output_bytes=1_048_576)

    document = IsccTikaExtractor(policy, tmp_path).extract(source, occurrence)

    assert expected in document.text
    assert document.extractor_profile == "iscc-tika"
    assert document.metadata["tool_version"] == "0.6.0"


def test_native_tika_ocr_profile_explicitly_opts_in(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    commands: list[tuple[str, ...]] = []

    def run(command: tuple[str, ...], **kwargs: object) -> CommandResult:
        commands.append(command)
        payload = {
            "text": "ocr text",
            "metadata": {"pdf:charsPerPage": ["0"]},
            "version": "0.6.0",
        }
        return CommandResult(json.dumps(payload).encode("ascii"), b"")

    monkeypatch.setattr(iscc_tika, "run_command", run)
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"%PDF-scan")
    occurrence = SourceOccurrence("one", "scan.pdf", "scan", content_hash="a" * 64)

    document = IsccTikaExtractor(
        ExtractionPolicy(ocr_languages="rus+eng+deu+ukr"),
        tmp_path,
        ocr_enabled=True,
    ).extract(source, occurrence)

    assert document.extractor_profile == "iscc-tika-ocr"
    assert commands[0][-2:] == ("ocr", "rus+eng+deu+ukr")
    assert (document.anchors[0].start_char, document.anchors[0].end_char) == (0, 8)
    assert document.anchors[0].page == 1

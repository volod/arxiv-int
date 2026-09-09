"""Docling CLI adapter for PDF layout and table evidence."""

import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy
from arxiv_int.extraction.process import run_command, tool_version
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.interfaces.sources import BoundingBox, SourceAnchor, SourceOccurrence


class DoclingExtractor:
    """Convert a bounded local document to Docling JSON without implicit OCR."""

    name = "docling"
    feature = "extraction"

    def __init__(self, policy: ExtractionPolicy, scratch: Path, artifacts: Path) -> None:
        self.policy = policy
        self.scratch = scratch
        self.artifacts = artifacts
        self._version: str | None = None

    def supports(self, media_type: str) -> bool:
        return media_type in {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.oasis.opendocument.spreadsheet",
        }

    def extract(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        if source.stat().st_size > self.policy.input_bytes:
            raise ExtractionError(
                "input-size-limit",
                f"source exceeds extraction limit of {self.policy.input_bytes} bytes",
            )
        with tempfile.TemporaryDirectory(dir=self.scratch) as directory:
            output = Path(directory)
            run_command(
                (
                    str(Path(sys.executable).with_name("docling")),
                    str(source),
                    "--to",
                    "json",
                    "--output",
                    str(output),
                    "--no-ocr",
                    "--abort-on-error",
                    "--artifacts-path",
                    str(self.artifacts),
                ),
                timeout_seconds=self.policy.timeout_seconds,
                output_bytes=self.policy.output_bytes,
                scratch=self.scratch,
                environment={
                    "HF_HUB_OFFLINE": "1",
                    "TRANSFORMERS_OFFLINE": "1",
                    "DOCLING_ARTIFACTS_PATH": str(self.artifacts),
                },
            )
            candidates = list(output.glob("*.json"))
            if len(candidates) != 1:
                raise ExtractionError(
                    "docling-invalid-output",
                    f"Docling produced {len(candidates)} JSON outputs",
                )
            if candidates[0].stat().st_size > self.policy.output_bytes:
                raise ExtractionError(
                    "tool-output-limit",
                    f"Docling output exceeded {self.policy.output_bytes} bytes",
                )
            try:
                payload: Any = json.loads(candidates[0].read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
                raise ExtractionError(
                    "docling-invalid-output", "Docling returned invalid JSON"
                ) from error
        if not isinstance(payload, dict):
            raise ExtractionError("docling-invalid-output", "Docling root is not an object")
        if self._version is None:
            self._version = tool_version(
                (str(Path(sys.executable).with_name("docling")), "--version"),
                timeout_seconds=30,
                output_bytes=4096,
                scratch=self.scratch,
            )
        return _document(
            payload,
            occurrence,
            self._version,
            self.policy.spans_per_document,
            _media_type(source),
        )


def _document(
    payload: dict[str, Any],
    occurrence: SourceOccurrence,
    version: str,
    span_limit: int,
    media_type: str = "application/pdf",
) -> ExtractedDocument:
    parts: list[str] = []
    anchors: list[SourceAnchor] = []
    offset = 0
    for item in _items(payload, "texts"):
        offset = _append(parts, anchors, item, occurrence, str(item.get("label", "text")), offset)
    for table in _items(payload, "tables"):
        data = table.get("data")
        if not isinstance(data, dict):
            continue
        sheet = str(table.get("name") or table.get("sheet_name") or "")
        for cell in _items(data, "table_cells"):
            if sheet and not (cell.get("sheet") or cell.get("sheet_name")):
                cell = {**cell, "sheet": sheet}
            offset = _append(parts, anchors, cell, occurrence, "table-cell", offset)
    if len(anchors) > span_limit:
        raise ExtractionError("span-limit", f"Docling produced more than {span_limit} spans")
    return ExtractedDocument(
        text="".join(parts),
        media_type=media_type,
        occurrence=occurrence,
        extractor_profile="docling",
        anchors=tuple(anchors),
        metadata={"tool_version": version, "layout": "true"},
    )


def _append(
    parts: list[str],
    anchors: list[SourceAnchor],
    item: dict[str, Any],
    occurrence: SourceOccurrence,
    kind: str,
    offset: int,
) -> int:
    text = item.get("text")
    if not isinstance(text, str) or not text:
        return offset
    start = offset
    if parts:
        parts.append("\n")
        start += 1
    parts.append(text)
    end = start + len(text)
    provenance = item.get("prov")
    prov = provenance[0] if isinstance(provenance, list) and provenance else {}
    if not isinstance(prov, dict):
        prov = {}
    row = item.get("start_row_offset_idx")
    column = item.get("start_col_offset_idx")
    anchors.append(
        SourceAnchor(
            occurrence,
            start_char=start,
            end_char=end,
            page=_integer(prov.get("page_no")),
            sheet=str(item.get("sheet_name") or item.get("sheet") or ""),
            row=_integer(row),
            column=_integer(column),
            bbox=_bbox(prov.get("bbox")),
            kind=kind,
        )
    )
    return end


def _items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    values = payload.get(key, [])
    return [item for item in values if isinstance(item, dict)] if isinstance(values, list) else []


def _integer(value: Any) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None


def _bbox(value: Any) -> BoundingBox | None:
    if not isinstance(value, dict):
        return None
    keys = (
        ("l", "t", "r", "b")
        if all(key in value for key in ("l", "t", "r", "b"))
        else (
            "x0",
            "y0",
            "x1",
            "y1",
        )
    )
    try:
        coordinates = [float(value[key]) for key in keys]
    except (KeyError, TypeError, ValueError):
        return None
    return BoundingBox(*coordinates)


def _media_type(source: Path) -> str:
    if source.suffix.lower() == ".xlsx":
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    if source.suffix.lower() == ".ods":
        return "application/vnd.oasis.opendocument.spreadsheet"
    return "application/pdf"

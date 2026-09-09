"""Isolated native iscc-tika adapter for broad format coverage."""

import json
import sys
from pathlib import Path
from typing import Any

from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy
from arxiv_int.extraction.process import run_command
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.interfaces.sources import SourceAnchor, SourceOccurrence


class IsccTikaExtractor:
    """Run the native Python binding in a killable bounded child process."""

    name = "iscc-tika"
    feature = "extraction"

    def __init__(
        self, policy: ExtractionPolicy, scratch: Path, *, ocr_enabled: bool = False
    ) -> None:
        self.policy = policy
        self.scratch = scratch
        self.ocr_enabled = ocr_enabled
        self.name = "iscc-tika-ocr" if ocr_enabled else "iscc-tika"

    def supports(self, media_type: str) -> bool:
        return media_type != "application/octet-stream"

    def extract(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        if source.stat().st_size > self.policy.input_bytes:
            raise ExtractionError(
                "input-size-limit",
                f"source exceeds extraction limit of {self.policy.input_bytes} bytes",
            )
        result = run_command(
            (
                sys.executable,
                "-m",
                "arxiv_int.extraction.iscc_worker",
                str(source),
                str(self.policy.output_bytes),
                "ocr" if self.ocr_enabled else "baseline",
                self.policy.ocr_languages,
            ),
            timeout_seconds=self.policy.timeout_seconds,
            output_bytes=self.policy.output_bytes * 2,
            scratch=self.scratch,
        )
        try:
            payload: Any = json.loads(result.stdout)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ExtractionError(
                "tika-invalid-output", "iscc-tika worker returned invalid JSON"
            ) from error
        if not isinstance(payload, dict) or not isinstance(payload.get("text"), str):
            raise ExtractionError("tika-invalid-output", "iscc-tika worker omitted extracted text")
        text = payload["text"]
        metadata = payload.get("metadata", {})
        if not isinstance(metadata, dict):
            metadata = {}
        media_type = _first(metadata.get("Content-Type")) or "application/octet-stream"
        title = _first(metadata.get("dc:title"))
        anchors = _anchors(text, metadata, occurrence, self.ocr_enabled)
        return ExtractedDocument(
            text=text,
            media_type=media_type.split(";")[0],
            occurrence=occurrence,
            extractor_profile=self.name,
            anchors=anchors,
            metadata={
                "title": title,
                "tool_version": str(payload.get("version", "unknown"))[:200],
                "parsed_by": ",".join(_strings(metadata.get("X-TIKA:Parsed-By")))[:1000],
            },
        )


def _first(value: Any) -> str:
    values = _strings(value)
    return values[0] if values else ""


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)] if value is not None else []


def _anchors(
    text: str,
    metadata: dict[str, Any],
    occurrence: SourceOccurrence,
    ocr_enabled: bool,
) -> tuple[SourceAnchor, ...]:
    if not text:
        return ()
    counts = _strings(metadata.get("pdf:charsPerPage"))
    try:
        lengths = [int(value) for value in counts]
    except ValueError:
        lengths = []
    if lengths and all(length >= 0 for length in lengths) and 0 < sum(lengths) <= len(text):
        lengths[-1] += len(text) - sum(lengths)
        anchors = []
        offset = 0
        for page, length in enumerate(lengths, start=1):
            anchors.append(
                SourceAnchor(
                    occurrence,
                    start_char=offset,
                    end_char=offset + length,
                    page=page,
                    kind="ocr-page" if ocr_enabled else "page",
                )
            )
            offset += length
        return tuple(anchors)
    return (
        SourceAnchor(
            occurrence,
            start_char=0,
            end_char=len(text),
            page=1 if lengths and all(length >= 0 for length in lengths) else None,
            kind="ocr-text" if ocr_enabled else "text",
        ),
    )

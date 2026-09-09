from pathlib import Path

import pytest

from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy
from arxiv_int.extraction.router import TieredExtractor
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.interfaces.sources import SourceAnchor, SourceOccurrence


class FakeExtractor:
    feature = "extraction"

    def __init__(self, name: str, text: str = "", failure: str | None = None) -> None:
        self.name = name
        self.text = text
        self.failure = failure
        self.calls = 0

    def supports(self, media_type: str) -> bool:
        return True

    def extract(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        self.calls += 1
        if self.failure:
            raise ExtractionError(self.failure, f"{self.name} unavailable")
        return ExtractedDocument(
            self.text,
            "application/pdf",
            occurrence,
            self.name,
            (SourceAnchor(occurrence, start_char=0, end_char=len(self.text), kind="text"),),
        )


@pytest.fixture
def occurrence() -> SourceOccurrence:
    return SourceOccurrence("one", "report.pdf", "scan", content_hash="a" * 64)


def test_layout_pdf_uses_docling_after_tika_baseline(
    tmp_path: Path, occurrence: SourceOccurrence
) -> None:
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x" * 100)
    baseline = FakeExtractor("tika", "baseline text with enough characters for digital PDF")
    layout = FakeExtractor("docling", "layout table text")
    ocr = FakeExtractor("ocr", "ocr text")
    router = TieredExtractor(
        baseline,
        layout,
        ocr,
        ExtractionPolicy(scanned_pdf_min_chars=10, scanned_pdf_chars_per_kib=0.01),
    )

    result = router.extract(source, occurrence, "application/pdf", None)

    assert result.extractor_profile == "docling"
    assert (baseline.calls, layout.calls, ocr.calls) == (1, 1, 0)


def test_scanned_pdf_opts_into_ocr(tmp_path: Path, occurrence: SourceOccurrence) -> None:
    source = tmp_path / "scan.pdf"
    source.write_bytes(b"x" * 100)
    baseline = FakeExtractor("tika", "")
    layout = FakeExtractor("docling", "")
    ocr = FakeExtractor("iscc-tika-ocr", "recognized text")
    router = TieredExtractor(
        baseline,
        layout,
        ocr,
        ExtractionPolicy(scanned_pdf_min_chars=10, scanned_pdf_chars_per_kib=0.01),
    )

    result = router.extract(source, occurrence, "application/pdf", None)

    assert result.extractor_profile == "iscc-tika-ocr"
    assert (baseline.calls, layout.calls, ocr.calls) == (1, 1, 1)


def test_layout_failure_preserves_tika_fallback_reason(
    tmp_path: Path, occurrence: SourceOccurrence
) -> None:
    source = tmp_path / "report.pdf"
    source.write_bytes(b"x" * 100)
    baseline = FakeExtractor("tika", "digital text")
    layout = FakeExtractor("docling", failure="tool-unavailable")
    router = TieredExtractor(
        baseline,
        layout,
        FakeExtractor("ocr"),
        ExtractionPolicy(scanned_pdf_min_chars=5, scanned_pdf_chars_per_kib=0.01),
    )

    result = router.extract(source, occurrence, "application/pdf", None)

    assert result.extractor_profile == "tika"
    assert result.metadata["fallback_reasons"] == "tool-unavailable"


def test_invalid_anchor_is_refused(tmp_path: Path, occurrence: SourceOccurrence) -> None:
    class InvalidExtractor(FakeExtractor):
        def extract(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
            other = SourceOccurrence("two", "other.pdf", "scan")
            return ExtractedDocument(
                "text",
                "application/pdf",
                occurrence,
                self.name,
                (SourceAnchor(other, start_char=0, end_char=4),),
            )

    router = TieredExtractor(
        InvalidExtractor("invalid"),
        FakeExtractor("layout"),
        FakeExtractor("ocr"),
        ExtractionPolicy(),
    )
    source = tmp_path / "file.bin"
    source.write_bytes(b"x")

    with pytest.raises(ExtractionError, match="anchor occurrence"):
        router.extract(source, occurrence, "application/octet-stream", None)

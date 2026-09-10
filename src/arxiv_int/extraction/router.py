"""Selection policy composing Tika, Docling, and OCR lanes."""

from dataclasses import replace
from pathlib import Path

from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy
from arxiv_int.extraction.text import PlainTextExtractor
from arxiv_int.interfaces.extraction import DocumentExtractor, ExtractedDocument
from arxiv_int.interfaces.sources import SourceOccurrence

_LAYOUT_MEDIA_TYPES = {
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.oasis.opendocument.spreadsheet",
}


class TieredExtractor:
    """Select a lane and retain explicit fallback evidence."""

    def __init__(
        self,
        baseline: DocumentExtractor,
        layout: DocumentExtractor,
        ocr: DocumentExtractor,
        policy: ExtractionPolicy,
    ) -> None:
        self.baseline = baseline
        self.layout = layout
        self.ocr = ocr
        self.policy = policy

    def extract(
        self,
        source: Path,
        occurrence: SourceOccurrence,
        media_type: str,
        encoding: str | None,
    ) -> ExtractedDocument:
        """Extract one source with deterministic routing and bounded fallbacks."""
        if media_type == "text/plain":
            try:
                return self._checked(
                    PlainTextExtractor(self.policy, encoding).extract(source, occurrence)
                )
            except ExtractionError:
                return self._attempt(source, occurrence, (self.baseline,))
        if media_type.startswith("image/"):
            return self._attempt(source, occurrence, (self.ocr,))
        if media_type in _LAYOUT_MEDIA_TYPES:
            return self._extract_layout(source, occurrence)
        if media_type != "application/pdf":
            return self._attempt(source, occurrence, (self.baseline,))
        return self._extract_pdf(source, occurrence)

    def _extract_pdf(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        """Apply baseline, OCR, and layout policy to one PDF."""
        failures: list[ExtractionError] = []
        baseline = self._try(source, occurrence, self.baseline, failures)
        if baseline is not None:
            layout = self._try(source, occurrence, self.layout, failures)
            if layout is not None and layout.text.strip():
                return self._with_fallback(layout, failures)
            if self._looks_scanned(baseline, source.stat().st_size):
                ocr = self._try(source, occurrence, self.ocr, failures)
                return self._with_fallback(ocr or baseline, failures)
            return self._with_fallback(baseline, failures)
        layout = self._try(source, occurrence, self.layout, failures)
        if layout is not None and layout.text.strip():
            return self._with_fallback(layout, failures)
        ocr = self._try(source, occurrence, self.ocr, failures)
        if ocr is not None:
            return self._with_fallback(ocr, failures)
        raise _combined(failures)

    def _extract_layout(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        """Prefer structured layout output while retaining baseline fallback."""
        failures: list[ExtractionError] = []
        baseline = self._try(source, occurrence, self.baseline, failures)
        layout = self._try(source, occurrence, self.layout, failures)
        candidate = layout if layout is not None and layout.text.strip() else baseline
        if candidate is None:
            raise _combined(failures)
        return self._with_fallback(candidate, failures)

    def _attempt(
        self,
        source: Path,
        occurrence: SourceOccurrence,
        extractors: tuple[DocumentExtractor, ...],
    ) -> ExtractedDocument:
        failures: list[ExtractionError] = []
        for extractor in extractors:
            result = self._try(source, occurrence, extractor, failures)
            if result is not None:
                return self._with_fallback(result, failures)
        raise _combined(failures)

    def _try(
        self,
        source: Path,
        occurrence: SourceOccurrence,
        extractor: DocumentExtractor,
        failures: list[ExtractionError],
    ) -> ExtractedDocument | None:
        try:
            return self._checked(extractor.extract(source, occurrence))
        except ExtractionError as error:
            failures.append(error)
            return None
        except (OSError, RuntimeError, ValueError) as error:
            failures.append(
                ExtractionError(
                    "extractor-failed",
                    f"{extractor.name} failed with {type(error).__name__}",
                )
            )
            return None

    def _checked(self, document: ExtractedDocument) -> ExtractedDocument:
        if len(document.text.encode("utf-8")) > self.policy.output_bytes:
            raise ExtractionError(
                "text-output-limit",
                f"extracted text exceeded {self.policy.output_bytes} bytes",
            )
        if len(document.anchors) > self.policy.spans_per_document:
            raise ExtractionError(
                "span-limit",
                f"extractor produced more than {self.policy.spans_per_document} spans",
            )
        for anchor in document.anchors:
            if anchor.occurrence != document.occurrence:
                raise ExtractionError("invalid-anchor", "anchor occurrence differs from document")
            if (
                anchor.start_char is not None
                and anchor.end_char is not None
                and anchor.end_char > len(document.text)
            ):
                raise ExtractionError("invalid-anchor", "anchor exceeds extracted text")
        return document

    def _looks_scanned(self, document: ExtractedDocument, size: int) -> bool:
        minimum = max(
            self.policy.scanned_pdf_min_chars,
            int((size / 1024) * self.policy.scanned_pdf_chars_per_kib),
        )
        return len(document.text.strip()) < minimum

    @staticmethod
    def _with_fallback(
        document: ExtractedDocument, failures: list[ExtractionError]
    ) -> ExtractedDocument:
        if not failures:
            return document
        metadata = dict(document.metadata)
        metadata["fallback_reasons"] = ",".join(error.reason for error in failures)
        return replace(document, metadata=metadata)


def _combined(failures: list[ExtractionError]) -> ExtractionError:
    if not failures:
        return ExtractionError("unsupported-format", "no extractor supports the source format")
    reasons = ",".join(error.reason for error in failures)
    details = "; ".join(error.detail for error in failures)
    return ExtractionError("all-extractors-failed", f"{reasons}: {details}")

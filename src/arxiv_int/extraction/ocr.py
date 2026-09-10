"""OCRmyPDF and Tesseract adapters for scanned PDFs and images."""

import csv
import tempfile
from pathlib import Path

from arxiv_int.extraction.iscc_tika import IsccTikaExtractor
from arxiv_int.extraction.model import ExtractionError, ExtractionPolicy
from arxiv_int.extraction.process import run_command, tool_version
from arxiv_int.interfaces.extraction import ExtractedDocument
from arxiv_int.interfaces.sources import BoundingBox, SourceAnchor, SourceOccurrence


class OcrExtractor:
    """Run bounded local OCR while preserving page and image coordinates."""

    name = "ocr"
    feature = "extraction"

    def __init__(self, policy: ExtractionPolicy, scratch: Path) -> None:
        self.policy = policy
        self.scratch = scratch
        self._versions: dict[str, str] = {}
        self._pdf_ocr = IsccTikaExtractor(policy, scratch, ocr_enabled=True)

    def supports(self, media_type: str) -> bool:
        return media_type == "application/pdf" or media_type.startswith("image/")

    def extract(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        if source.stat().st_size > self.policy.input_bytes:
            raise ExtractionError(
                "input-size-limit",
                f"source exceeds extraction limit of {self.policy.input_bytes} bytes",
            )
        if source.suffix.lower() == ".pdf":
            return self._pdf_ocr.extract(source, occurrence)
        return self._image(source, occurrence)

    def _image(self, source: Path, occurrence: SourceOccurrence) -> ExtractedDocument:
        pixels = _image_pixels(source)
        maximum = self.policy.ocr_max_megapixels * 1_000_000
        if pixels is None or pixels > maximum:
            raise ExtractionError(
                "image-pixel-limit",
                f"image dimensions are invalid or exceed {self.policy.ocr_max_megapixels} megapixels",
            )
        with tempfile.TemporaryDirectory(dir=self.scratch) as directory:
            output = Path(directory) / "ocr"
            run_command(
                (
                    "tesseract",
                    str(source),
                    str(output),
                    "-l",
                    self.policy.ocr_languages,
                    "tsv",
                ),
                timeout_seconds=self.policy.timeout_seconds,
                output_bytes=self.policy.output_bytes,
                scratch=self.scratch,
            )
            tsv = output.with_suffix(".tsv")
            if not tsv.is_file() or tsv.stat().st_size > self.policy.output_bytes:
                raise ExtractionError("ocr-invalid-output", "Tesseract TSV is missing or oversized")
            text, anchors, confidence = _read_tsv(tsv, occurrence, self.policy.spans_per_document)
        return ExtractedDocument(
            text=text,
            media_type="image",
            occurrence=occurrence,
            extractor_profile="tesseract",
            anchors=anchors,
            metadata={
                "tool_version": self._version("tesseract", ("tesseract", "--version")),
                "mean_confidence": f"{confidence:.3f}",
            },
        )

    def _version(self, key: str, command: tuple[str, ...]) -> str:
        if key not in self._versions:
            self._versions[key] = tool_version(
                command, timeout_seconds=30, output_bytes=4096, scratch=self.scratch
            )
        return self._versions[key]


def _read_tsv(
    path: Path, occurrence: SourceOccurrence, span_limit: int
) -> tuple[str, tuple[SourceAnchor, ...], float]:
    parts: list[str] = []
    anchors: list[SourceAnchor] = []
    confidence: list[float] = []
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            word = row.get("text", "").strip()
            if not word:
                continue
            if len(anchors) >= span_limit:
                raise ExtractionError(
                    "span-limit", f"Tesseract produced more than {span_limit} spans"
                )
            start = sum(len(part) for part in parts)
            if parts:
                parts.append(" ")
                start += 1
            parts.append(word)
            left = _int(row, "left")
            top = _int(row, "top")
            width = _int(row, "width")
            height = _int(row, "height")
            anchors.append(
                SourceAnchor(
                    occurrence,
                    start_char=start,
                    end_char=start + len(word),
                    page=max(1, _int(row, "page_num")),
                    bbox=BoundingBox(left, top, left + width, top + height),
                    kind="ocr-word",
                )
            )
            try:
                value = float(row.get("conf", "-1"))
            except ValueError:
                value = -1
            if value >= 0:
                confidence.append(value)
    mean = sum(confidence) / len(confidence) if confidence else 0.0
    return "".join(parts), tuple(anchors), mean


def _int(row: dict[str, str | None], key: str) -> int:
    try:
        return max(0, int(row.get(key) or "0"))
    except ValueError:
        return 0


def _image_pixels(path: Path) -> int | None:
    with path.open("rb") as handle:
        sample = handle.read(1_048_576)
    if sample.startswith(b"\x89PNG\r\n\x1a\n") and len(sample) >= 24:
        width = int.from_bytes(sample[16:20], "big")
        height = int.from_bytes(sample[20:24], "big")
        return width * height
    if sample.startswith(b"\xff\xd8"):
        return _jpeg_pixels(sample)
    return None


def _jpeg_pixels(payload: bytes) -> int | None:
    offset = 2
    start_of_frame = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while offset + 4 <= len(payload):
        if payload[offset] != 0xFF:
            offset += 1
            continue
        marker = payload[offset + 1]
        offset += 2
        if marker in {0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        length = int.from_bytes(payload[offset : offset + 2], "big")
        if length < 2 or offset + length > len(payload):
            return None
        if marker in start_of_frame and length >= 7:
            height = int.from_bytes(payload[offset + 3 : offset + 5], "big")
            width = int.from_bytes(payload[offset + 5 : offset + 7], "big")
            return width * height
        offset += length
    return None

"""Typed extraction policy, inventory inputs, and failure outcomes."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class ExtractionPolicy:
    """Fingerprintable ceilings and lane-selection thresholds."""

    input_bytes: int = 67_108_864
    output_bytes: int = 33_554_432
    timeout_seconds: int = 300
    batch_rows: int = 256
    spans_per_document: int = 20_000
    scanned_pdf_min_chars: int = 64
    scanned_pdf_chars_per_kib: float = 0.5
    ocr_languages: str = "rus+eng+deu+ukr"
    ocr_max_megapixels: int = 25

    def __post_init__(self) -> None:
        if any(value <= 0 for name, value in asdict(self).items() if name != "ocr_languages"):
            raise ValueError("extraction limits must be positive")
        if not self.ocr_languages:
            raise ValueError("OCR languages must not be empty")


@dataclass(frozen=True, slots=True)
class InventoryInput:
    """One published inventory observation consumed by extraction."""

    occurrence_id: str
    silo_id: str
    relative_path: str
    members: tuple[str, ...]
    content_hash: str | None
    size: int
    media_type: str
    encoding: str | None
    status: str
    reason: str | None


class ExtractionError(RuntimeError):
    """A safe, actionable per-document extraction refusal."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(detail)
        self.reason = reason
        self.detail = detail


DEFAULT_POLICY = ExtractionPolicy()

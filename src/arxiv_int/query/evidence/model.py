"""Typed sealed-manifest contracts for citations, path events, and locations."""

from dataclasses import dataclass

from arxiv_int.interfaces.sources import CoordinateSpace
from arxiv_int.interfaces.tokens import require_relative_path, require_token
from arxiv_int.query.evidence.schema import ContractRow

CATALOG_SCHEMA = "arxiv-int.evidence-catalog.v1"
LEDGER_SCHEMA = "arxiv-int.path-event-ledger.v1"
RESOLUTION_SCHEMA = "arxiv-int.evidence-resolution.v1"
IMPORT_SCHEMA = "arxiv-int.path-event-import.v1"
CITATION_KINDS = frozenset({"content", "fact", "report"})
LOCATION_STATUSES = frozenset({"matching", "missing", "changed", "escaped", "unchecked"})
COPY_KIND = "copy"
DocumentRecord = ContractRow
OccurrenceRecord = ContractRow
PathEvent = ContractRow


class EvidenceError(ValueError):
    """Raised when a sealed catalog, ledger, or citation cannot be used."""

    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


@dataclass(frozen=True, slots=True)
class EvidenceAnchor:
    """Page, cell, or member coordinates in original or normalized space."""

    space: CoordinateSpace = "original"
    start_char: int | None = None
    end_char: int | None = None
    page: int | None = None
    sheet: str = ""
    cell_range: str = ""
    row: int | None = None
    column: int | None = None
    kind: str = ""
    container_path: str = ""
    member_path: str = ""

    def __post_init__(self) -> None:
        if (
            self.start_char is not None
            and self.end_char is not None
            and self.end_char < self.start_char
        ):
            raise ValueError("end_char must be greater than or equal to start_char")
        if self.container_path:
            require_relative_path(self.container_path, "container_path")
        if self.member_path:
            require_relative_path(self.member_path, "member_path")


@dataclass(frozen=True, slots=True)
class Citation:
    """Content, fact, or report pointer with original and normalized anchors."""

    kind: str
    citation_id: str
    document_id: str
    fact_id: str = ""
    report_id: str = ""
    span_id: str = ""
    original: EvidenceAnchor | None = None
    normalized: EvidenceAnchor | None = None

    def __post_init__(self) -> None:
        if self.kind not in CITATION_KINDS:
            raise ValueError(f"unknown citation kind {self.kind!r}")
        require_token(self.citation_id, "citation_id")
        if self.document_id:
            require_token(self.document_id, "document_id")


@dataclass(frozen=True, slots=True)
class EvidenceCatalog:
    """Sealed documents, occurrences, citations, and path events."""

    documents: tuple[DocumentRecord, ...]
    occurrences: tuple[OccurrenceRecord, ...]
    citations: tuple[Citation, ...] = ()
    events: tuple[PathEvent, ...] = ()
    schema: str = CATALOG_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != CATALOG_SCHEMA:
            raise ValueError(f"unsupported evidence-catalog schema {self.schema!r}")

    def with_events(self, events: tuple[PathEvent, ...]) -> "EvidenceCatalog":
        """Return a catalog that overlays additional path events without copying rows."""
        return EvidenceCatalog(
            self.documents,
            self.occurrences,
            self.citations,
            (*self.events, *events),
            self.schema,
        )


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """One original/current physical location after path-event overlay."""

    silo_id: str
    original_path: str
    current_path: str
    content_hash: str
    status: str
    scan_id: str = ""
    occurrence_id: str = ""
    container_path: str = ""
    member_path: str = ""
    role: str = "source"

    def __post_init__(self) -> None:
        if self.status not in LOCATION_STATUSES:
            raise ValueError(f"unknown location status {self.status!r}")


@dataclass(frozen=True, slots=True)
class EvidenceResolution:
    """Read-only resolution of one citation to every known source location."""

    citation: Citation
    document_id: str
    content_hash: str
    locations: tuple[SourceLocation, ...]
    original_anchor: EvidenceAnchor | None = None
    normalized_anchor: EvidenceAnchor | None = None
    extractor_profile: str = ""
    ambiguous: bool = False
    findings: tuple[str, ...] = ()
    schema: str = RESOLUTION_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != RESOLUTION_SCHEMA:
            raise ValueError(f"unsupported evidence-resolution schema {self.schema!r}")


@dataclass(frozen=True, slots=True)
class ImportReport:
    """Result of an idempotent portable ledger merge."""

    ledger_id: str
    inserted: int
    skipped: int
    refused: int
    findings: tuple[str, ...] = ()
    schema: str = IMPORT_SCHEMA

    def __post_init__(self) -> None:
        if self.schema != IMPORT_SCHEMA:
            raise ValueError(f"unsupported path-event-import schema {self.schema!r}")

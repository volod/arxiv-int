"""JSON codecs for sealed evidence catalogs and path-event ledgers."""

from typing import Any

from arxiv_int.query.evidence.model import (
    Citation,
    DocumentRecord,
    EvidenceAnchor,
    EvidenceCatalog,
    EvidenceError,
    OccurrenceRecord,
    PathEvent,
)


def catalog_from_payload(payload: dict[str, Any], schema: str) -> EvidenceCatalog:
    """Build a catalog from a JSON object."""
    return EvidenceCatalog(
        documents=tuple(_document(item) for item in payload.get("documents") or ()),
        occurrences=tuple(_occurrence(item) for item in payload.get("occurrences") or ()),
        citations=tuple(_citation(item) for item in payload.get("citations") or ()),
        events=tuple(event_from_payload(item) for item in payload.get("events") or ()),
        schema=schema,
    )


def catalog_payload(catalog: EvidenceCatalog) -> dict[str, Any]:
    """Return a canonical JSON object for one catalog."""
    return {
        "citations": [_citation_payload(item) for item in catalog.citations],
        "documents": [
            {
                "content_hash": item.content_hash,
                "document_id": item.document_id,
                "extractor_profile": item.extractor_profile,
            }
            for item in catalog.documents
        ],
        "events": [event_payload(item) for item in catalog.events],
        "occurrences": [_occurrence_payload(item) for item in catalog.occurrences],
        "schema": catalog.schema,
    }


def event_from_payload(raw: object) -> PathEvent:
    """Parse one path-event row."""
    item = _object(raw, "path event")
    return PathEvent(
        event_id=_text(item, "event_id"),
        document_id=_text(item, "document_id"),
        silo_id=_text(item, "silo_id"),
        kind=_text(item, "kind"),
        relative_path=_text(item, "relative_path"),
        content_hash=_text(item, "content_hash"),
        previous_relative_path=_text(item, "previous_relative_path"),
        occurrence_id=_text(item, "occurrence_id"),
        ledger_id=_text(item, "ledger_id"),
        recorded_at=_text(item, "recorded_at"),
        generation_id=_text(item, "generation_id"),
        contract_version=_text(item, "contract_version") or "1.0.0",
    )


def event_payload(item: PathEvent) -> dict[str, str]:
    """Serialize one path-event row."""
    return {
        "content_hash": item.content_hash,
        "contract_version": item.contract_version,
        "document_id": item.document_id,
        "event_id": item.event_id,
        "generation_id": item.generation_id,
        "kind": item.kind,
        "ledger_id": item.ledger_id,
        "occurrence_id": item.occurrence_id,
        "previous_relative_path": item.previous_relative_path,
        "recorded_at": item.recorded_at,
        "relative_path": item.relative_path,
        "silo_id": item.silo_id,
    }


def _document(raw: object) -> DocumentRecord:
    item = _object(raw, "document")
    return DocumentRecord(
        document_id=_text(item, "document_id"),
        content_hash=_text(item, "content_hash"),
        extractor_profile=_text(item, "extractor_profile"),
    )


def _occurrence(raw: object) -> OccurrenceRecord:
    item = _object(raw, "occurrence")
    return OccurrenceRecord(
        document_id=_text(item, "document_id"),
        silo_id=_text(item, "silo_id"),
        relative_path=_text(item, "relative_path"),
        scan_id=_text(item, "scan_id"),
        content_hash=_text(item, "content_hash"),
        container_path=_text(item, "container_path"),
        member_path=_text(item, "member_path"),
        occurrence_id=_text(item, "occurrence_id"),
    )


def _citation(raw: object) -> Citation:
    item = _object(raw, "citation")
    return Citation(
        kind=_text(item, "kind") or "content",
        citation_id=_text(item, "citation_id"),
        document_id=_text(item, "document_id"),
        fact_id=_text(item, "fact_id"),
        report_id=_text(item, "report_id"),
        span_id=_text(item, "span_id"),
        original=_anchor(item.get("original")),
        normalized=_anchor(item.get("normalized")),
    )


def _anchor(raw: object) -> EvidenceAnchor | None:
    if raw is None:
        return None
    item = _object(raw, "anchor")
    space = _text(item, "space") or "original"
    if space not in {"original", "normalized"}:
        raise EvidenceError(f"unknown coordinate space {space!r}")
    row = item.get("row")
    column = item.get("column")
    page = item.get("page")
    start = item.get("start_char")
    end = item.get("end_char")
    return EvidenceAnchor(
        space=space,  # type: ignore[arg-type]
        start_char=None if start is None else int(start),
        end_char=None if end is None else int(end),
        page=None if page is None else int(page),
        sheet=_text(item, "sheet"),
        cell_range=_text(item, "cell_range"),
        row=None if row is None else int(row),
        column=None if column is None else int(column),
        kind=_text(item, "kind"),
        container_path=_text(item, "container_path"),
        member_path=_text(item, "member_path"),
    )


def _occurrence_payload(item: OccurrenceRecord) -> dict[str, str]:
    return {
        "container_path": item.container_path,
        "content_hash": item.content_hash,
        "document_id": item.document_id,
        "member_path": item.member_path,
        "occurrence_id": item.identity,
        "relative_path": item.relative_path,
        "scan_id": item.scan_id,
        "silo_id": item.silo_id,
    }


def _citation_payload(item: Citation) -> dict[str, Any]:
    return {
        "citation_id": item.citation_id,
        "document_id": item.document_id,
        "fact_id": item.fact_id,
        "kind": item.kind,
        "normalized": _anchor_payload(item.normalized),
        "original": _anchor_payload(item.original),
        "report_id": item.report_id,
        "span_id": item.span_id,
    }


def _anchor_payload(item: EvidenceAnchor | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "cell_range": item.cell_range,
        "column": item.column,
        "container_path": item.container_path,
        "end_char": item.end_char,
        "kind": item.kind,
        "member_path": item.member_path,
        "page": item.page,
        "row": item.row,
        "sheet": item.sheet,
        "space": item.space,
        "start_char": item.start_char,
    }


def _object(raw: object, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise EvidenceError(f"{label} must be a JSON object")
    return raw


def _text(item: dict[str, Any], key: str) -> str:
    value = item.get(key)
    if value is None:
        return ""
    return str(value)

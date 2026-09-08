"""Fixture builders for sealed evidence catalogs."""

import hashlib
from pathlib import Path

from arxiv_int.query.evidence.catalog import write_catalog, write_ledger
from arxiv_int.query.evidence.model import (
    DocumentRecord,
    EvidenceAnchor,
    EvidenceCatalog,
    OccurrenceRecord,
    PathEvent,
)


def sha256_bytes(payload: bytes) -> str:
    """Return the SHA-256 hex digest of payload bytes."""
    return hashlib.sha256(payload).hexdigest()


def write_source(root: Path, relative: str, payload: bytes) -> str:
    """Write a silo-relative file and return its content hash."""
    path = root.joinpath(*relative.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return sha256_bytes(payload)


def sealed_paths(tmp_path: Path) -> tuple[Path, Path]:
    """Return catalog and ledger paths under a disposable root."""
    evidence = tmp_path / "normalized" / "evidence"
    evidence.mkdir(parents=True)
    return evidence / "catalog.json", evidence / "path-events.json"


def document(document_id: str, content_hash: str, profile: str = "fixture") -> DocumentRecord:
    """Return one sealed document row."""
    return DocumentRecord(document_id, content_hash, profile)


def occurrence(
    document_id: str,
    silo_id: str,
    relative_path: str,
    content_hash: str,
    *,
    scan_id: str = "scan-1",
    container_path: str = "",
    member_path: str = "",
) -> OccurrenceRecord:
    """Return one sealed occurrence bound to a document."""
    return OccurrenceRecord(
        document_id=document_id,
        silo_id=silo_id,
        relative_path=relative_path,
        scan_id=scan_id,
        content_hash=content_hash,
        container_path=container_path,
        member_path=member_path,
    )


def event(
    event_id: str,
    document_id: str,
    silo_id: str,
    kind: str,
    relative_path: str,
    content_hash: str,
    *,
    previous: str = "",
    recorded_at: str = "2026-01-01T00:00:00Z",
    ledger_id: str = "org-1",
    occurrence_id: str = "",
) -> PathEvent:
    """Return one portable path-event row."""
    return PathEvent(
        event_id=event_id,
        document_id=document_id,
        silo_id=silo_id,
        kind=kind,
        relative_path=relative_path,
        content_hash=content_hash,
        previous_relative_path=previous,
        occurrence_id=occurrence_id,
        ledger_id=ledger_id,
        recorded_at=recorded_at,
    )


def cell_anchor() -> EvidenceAnchor:
    """Return a spreadsheet cell anchor in original space."""
    return EvidenceAnchor(
        space="original",
        sheet="Payments",
        cell_range="B2:B2",
        row=2,
        column=2,
        kind="cell",
    )


def member_anchor() -> EvidenceAnchor:
    """Return a nested-member page anchor in original space."""
    return EvidenceAnchor(
        space="original",
        page=2,
        kind="page",
        container_path="mail/bundle.zip",
        member_path="attachments/invoice.pdf",
    )


def save_catalog(path: Path, catalog: EvidenceCatalog) -> Path:
    """Write a sealed catalog and return the path."""
    write_catalog(path, catalog)
    return path


def save_ledger(path: Path, events: tuple[PathEvent, ...], ledger_id: str = "org-1") -> Path:
    """Write a portable ledger and return the path."""
    write_ledger(path, ledger_id, events)
    return path

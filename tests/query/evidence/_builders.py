"""Fixture builders for sealed evidence catalogs."""

import hashlib
from pathlib import Path

from arxiv_int.query.evidence.catalog import write_catalog, write_ledger
from arxiv_int.query.evidence.model import EvidenceAnchor, EvidenceCatalog
from arxiv_int.query.evidence.schema import (
    DEFAULT_CONTRACT_VERSION,
    DOCUMENTS_CONTRACT,
    FIXTURE_GENERATION_ID,
    OCCURRENCES_CONTRACT,
    PATH_EVENTS_CONTRACT,
    ContractRow,
    parse_row,
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


def document(document_id: str, content_hash: str, profile: str = "fixture") -> ContractRow:
    """Return one sealed document row from the documents contract."""
    return parse_row(
        DOCUMENTS_CONTRACT,
        {
            "document_id": document_id,
            "content_hash": content_hash,
            "extractor_profile": profile,
            "generation_id": FIXTURE_GENERATION_ID,
            "contract_version": DEFAULT_CONTRACT_VERSION,
        },
    )


def occurrence(
    silo_id: str,
    relative_path: str,
    content_hash: str,
    *,
    scan_id: str = "scan-1",
    container_path: str = "",
    member_path: str = "",
    occurrence_id: str = "",
) -> ContractRow:
    """Return one sealed occurrence from the source-occurrences contract."""
    token = occurrence_id or f"{silo_id}:{relative_path}:{scan_id}"
    payload: dict[str, str] = {
        "occurrence_id": token,
        "silo_id": silo_id,
        "relative_path": relative_path,
        "scan_id": scan_id,
        "content_hash": content_hash,
        "generation_id": FIXTURE_GENERATION_ID,
        "contract_version": DEFAULT_CONTRACT_VERSION,
    }
    if container_path:
        payload["container_path"] = container_path
    if member_path:
        payload["member_path"] = member_path
    return parse_row(OCCURRENCES_CONTRACT, payload)


def event(
    event_id: str,
    document_id: str,
    silo_id: str,
    kind: str,
    relative_path: str,
    content_hash: str,
    *,
    previous: str = "",
    event_time: str = "2026-01-01T00:00:00Z",
    ledger_id: str = "org-1",
    occurrence_id: str = "",
) -> ContractRow:
    """Return one portable path-event row from the document-path-events contract."""
    payload: dict[str, str] = {
        "event_id": event_id,
        "document_id": document_id,
        "silo_id": silo_id,
        "kind": kind,
        "relative_path": relative_path,
        "content_hash": content_hash,
        "event_time": event_time,
        "ledger_id": ledger_id,
        "generation_id": FIXTURE_GENERATION_ID,
        "contract_version": DEFAULT_CONTRACT_VERSION,
    }
    if previous:
        payload["previous_relative_path"] = previous
    if occurrence_id:
        payload["occurrence_id"] = occurrence_id
    return parse_row(PATH_EVENTS_CONTRACT, payload)


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


def save_ledger(path: Path, events: tuple[ContractRow, ...], ledger_id: str = "org-1") -> Path:
    """Write a portable ledger and return the path."""
    write_ledger(path, ledger_id, events)
    return path

"""Portable rows follow ODCS columns and refuse unknown fields."""

import pytest

from arxiv_int.query.evidence.codec import event_from_payload, event_payload
from arxiv_int.query.evidence.model import EvidenceError
from arxiv_int.query.evidence.overlay import overlay_events
from arxiv_int.query.evidence.schema import (
    DEFAULT_CONTRACT_VERSION,
    FIXTURE_GENERATION_ID,
    PATH_EVENTS_CONTRACT,
    ContractRowError,
    column_names,
    parse_row,
)
from tests.query.evidence._builders import event, sha256_bytes

_DIGEST = sha256_bytes(b"invoice-bytes")
_OVERLAY_COLUMNS = frozenset(
    {
        "content_hash",
        "document_id",
        "event_id",
        "event_time",
        "kind",
        "occurrence_id",
        "previous_relative_path",
        "relative_path",
        "silo_id",
    }
)


def test_overlay_and_ledger_columns_are_contract_fields() -> None:
    names = column_names(PATH_EVENTS_CONTRACT)
    assert names >= _OVERLAY_COLUMNS
    assert "recorded_at" not in names
    assert "document_id" in column_names("documents")
    assert "document_id" not in column_names("source-occurrences")


def test_path_event_round_trip_uses_contract_columns_only() -> None:
    item = event("ev-1", "doc-1", "alpha", "initial", "docs/a.pdf", _DIGEST)
    payload = event_payload(item)
    assert set(payload) <= column_names(PATH_EVENTS_CONTRACT)
    assert "recorded_at" not in payload
    assert "generation_id" in payload
    assert "contract_version" in payload
    assert "event_time" in payload
    restored = event_from_payload(payload)
    assert restored == item


def test_unknown_path_event_field_is_refused() -> None:
    with pytest.raises(EvidenceError, match="unknown field"):
        event_from_payload(
            {
                "event_id": "ev-1",
                "document_id": "doc-1",
                "silo_id": "alpha",
                "kind": "initial",
                "relative_path": "docs/a.pdf",
                "content_hash": _DIGEST,
                "event_time": "2026-01-01T00:00:00Z",
                "generation_id": FIXTURE_GENERATION_ID,
                "contract_version": DEFAULT_CONTRACT_VERSION,
                "recorded_at": "2026-01-01T00:00:00Z",
            }
        )


def test_missing_required_path_event_field_is_refused() -> None:
    with pytest.raises(EvidenceError, match="missing required field"):
        event_from_payload(
            {
                "event_id": "ev-1",
                "document_id": "doc-1",
                "silo_id": "alpha",
                "kind": "initial",
                "relative_path": "docs/a.pdf",
                "content_hash": _DIGEST,
                "event_time": "2026-01-01T00:00:00Z",
                "contract_version": DEFAULT_CONTRACT_VERSION,
            }
        )


def test_occurrence_document_id_is_not_a_contract_field() -> None:
    with pytest.raises(ContractRowError, match="unknown field"):
        parse_row(
            "source-occurrences",
            {
                "occurrence_id": "occ-1",
                "silo_id": "alpha",
                "relative_path": "docs/a.pdf",
                "scan_id": "scan-1",
                "content_hash": _DIGEST,
                "document_id": "doc-1",
                "generation_id": FIXTURE_GENERATION_ID,
                "contract_version": DEFAULT_CONTRACT_VERSION,
            },
        )


def test_overlay_sorts_by_event_time() -> None:
    first = event(
        "ev-2",
        "doc-1",
        "alpha",
        "rename",
        "docs/b.pdf",
        _DIGEST,
        previous="docs/a.pdf",
        event_time="2026-01-02T00:00:00Z",
    )
    second = event(
        "ev-1",
        "doc-1",
        "alpha",
        "initial",
        "docs/a.pdf",
        _DIGEST,
        event_time="2026-01-01T00:00:00Z",
    )
    from tests.query.evidence._builders import occurrence

    tracks = overlay_events(
        (occurrence("alpha", "docs/a.pdf", _DIGEST),),
        (first, second),
        "doc-1",
    )
    assert tracks[0].original_path == "docs/a.pdf"
    assert tracks[0].current_path == "docs/b.pdf"

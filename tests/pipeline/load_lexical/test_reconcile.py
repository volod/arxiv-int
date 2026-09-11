"""Load reconciliation requires the store to equal the snapshot and refuses drift."""

from unittest.mock import MagicMock

import pytest

from arxiv_int.pipeline.load_lexical.reconcile import (
    FULL_SCOPE,
    PARTIAL_SCOPE,
    Reconciliation,
    reconcile,
)


def _reconciliation(**overrides: object) -> Reconciliation:
    values: dict[str, object] = {
        "canonical_documents": 4,
        "canonical_chunks": 10,
        "projection_rows": 10,
        "unindexed_chunks": 0,
        "checksum_scope": FULL_SCOPE,
        "checksum_match": True,
        "retracted_chunks": 0,
        "detail": "",
    }
    values.update(overrides)
    return Reconciliation(**values)  # type: ignore[arg-type]


def test_full_scope_requires_counts_and_checksum_agreement() -> None:
    assert _reconciliation().ok is True
    assert _reconciliation(checksum_match=False).ok is False


def test_partial_scope_refuses_because_every_load_is_complete() -> None:
    assert _reconciliation(checksum_scope=PARTIAL_SCOPE).ok is False
    assert _reconciliation(checksum_scope=PARTIAL_SCOPE, checksum_match=False).ok is False


def _live(documents: int, chunks: int, projection_rows: int, unindexed: int) -> MagicMock:
    connection = MagicMock()
    connection.execute.return_value.scalar.side_effect = [
        documents,
        chunks,
        projection_rows,
        unindexed,
    ]
    return connection


def test_reconcile_is_full_when_the_store_equals_the_snapshot() -> None:
    result = reconcile(
        _live(4, 10, 10, 0),
        table="search.lexical_p_v1",
        loaded_chunks=10,
        loaded_checksum="same",
        projection_checksum="same",
        retracted_chunks=3,
    )
    assert result.checksum_scope == FULL_SCOPE
    assert result.ok is True
    assert result.retracted_chunks == 3


def test_reconcile_refuses_a_store_wider_than_the_snapshot() -> None:
    result = reconcile(
        _live(4, 12, 12, 0),
        table="search.lexical_p_v1",
        loaded_chunks=10,
        loaded_checksum="loaded",
        projection_checksum="wider",
    )
    assert result.checksum_scope == PARTIAL_SCOPE
    assert result.ok is False
    assert result.detail == "canonical store holds 12 chunks but this snapshot loaded 10"


@pytest.mark.parametrize(
    "overrides",
    (
        {"unindexed_chunks": 1},
        {"projection_rows": 9},
        {"projection_rows": 11},
    ),
)
def test_missing_or_extra_projection_rows_refuse(overrides: dict[str, object]) -> None:
    assert _reconciliation(**overrides).ok is False


def test_json_evidence_reports_the_decision_and_scope() -> None:
    payload = _reconciliation(detail="reconciled").as_json_dict()
    assert payload == {
        "canonicalChunks": 10,
        "canonicalDocuments": 4,
        "checksumMatch": True,
        "checksumScope": FULL_SCOPE,
        "detail": "reconciled",
        "ok": True,
        "projectionRows": 10,
        "retractedChunks": 0,
        "unindexedChunks": 0,
    }

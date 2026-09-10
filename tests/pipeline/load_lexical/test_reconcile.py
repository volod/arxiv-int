"""Load reconciliation accepts full and partial scopes and refuses drift."""

import pytest

from arxiv_int.pipeline.load_lexical.reconcile import (
    FULL_SCOPE,
    PARTIAL_SCOPE,
    Reconciliation,
)


def _reconciliation(**overrides: object) -> Reconciliation:
    values: dict[str, object] = {
        "canonical_documents": 4,
        "canonical_chunks": 10,
        "projection_rows": 10,
        "unindexed_chunks": 0,
        "checksum_scope": FULL_SCOPE,
        "checksum_match": True,
        "detail": "",
    }
    values.update(overrides)
    return Reconciliation(**values)  # type: ignore[arg-type]


def test_full_scope_requires_counts_and_checksum_agreement() -> None:
    assert _reconciliation().ok is True
    assert _reconciliation(checksum_match=False).ok is False


def test_partial_scope_accepts_a_wider_projection_checksum() -> None:
    partial = _reconciliation(checksum_scope=PARTIAL_SCOPE, checksum_match=False)
    assert partial.ok is True


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
        "unindexedChunks": 0,
    }

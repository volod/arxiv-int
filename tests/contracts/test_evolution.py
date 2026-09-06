"""Schema evolution behavior."""

import json

from arxiv_int.contracts.evolution import (
    CHANGE_ADDITIVE,
    CHANGE_BREAKING,
    CHANGE_IDENTICAL,
    classify_change,
    freeze_baseline,
    schema_snapshot,
    version_policy_errors,
)

_FIELD = {"logicalType": "string", "physicalType": "string", "required": True}
_OPTIONAL = {"logicalType": "string", "physicalType": "string", "required": False}


def test_change_classification_distinguishes_compatible_changes() -> None:
    assert classify_change({"id": _FIELD}, {"id": _FIELD}).change_class == CHANGE_IDENTICAL
    assert (
        classify_change({"id": _FIELD}, {"id": _FIELD, "title": _OPTIONAL}).change_class
        == CHANGE_ADDITIVE
    )
    assert classify_change({"id": _FIELD}, {"id": _OPTIONAL}).change_class == CHANGE_BREAKING


def test_version_policy_fails_closed() -> None:
    additive = classify_change({"id": _FIELD}, {"id": _FIELD, "title": _OPTIONAL})
    breaking = classify_change({"id": _FIELD}, {"id": _OPTIONAL})

    assert version_policy_errors("documents", "1.0.0", "1.0.1", additive)
    assert version_policy_errors("documents", "1.0.0", "1.1.0", additive) == ()
    assert version_policy_errors("documents", "1.0.0", "1.1.0", breaking)
    assert version_policy_errors("documents", "1.0.0", "2.0.0", breaking) == ()


def test_snapshot_and_baseline_are_byte_stable(tmp_path) -> None:
    contract = {
        "id": "documents",
        "version": "1.0.0",
        "schema": [{"properties": [{"name": "id", **_FIELD}]}],
    }
    snapshot = schema_snapshot(contract, "documents", fingerprints={"semanticMetadataHash": "abc"})
    destination = tmp_path / "evolution" / "documents.json"

    freeze_baseline(destination, snapshot)
    first = destination.read_bytes()
    freeze_baseline(destination, snapshot)

    assert destination.read_bytes() == first
    assert len(json.loads(first)["history"]) == 1

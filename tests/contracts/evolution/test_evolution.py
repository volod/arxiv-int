"""Schema evolution behavior."""

import json

import pytest

from arxiv_int.contracts.evolution import (
    CHANGE_ADDITIVE,
    CHANGE_BREAKING,
    CHANGE_IDENTICAL,
    FIELD_IDENTITY_SCHEMA_QUALIFIED,
    classify_change,
    freeze_baseline,
    migrate_schema_snapshot,
    schema_field_id,
    schema_snapshot,
    version_policy_errors,
)

_FIELD = {"logicalType": "string", "physicalType": "string", "required": True}
_OPTIONAL = {"logicalType": "string", "physicalType": "string", "required": False}


def test_change_classification_distinguishes_compatible_changes() -> None:
    left = schema_field_id("#0", "id")
    title = schema_field_id("#0", "title")
    assert classify_change({left: _FIELD}, {left: _FIELD}).change_class == CHANGE_IDENTICAL
    assert (
        classify_change({left: _FIELD}, {left: _FIELD, title: _OPTIONAL}).change_class
        == CHANGE_ADDITIVE
    )
    assert classify_change({left: _FIELD}, {left: _OPTIONAL}).change_class == CHANGE_BREAKING


def test_version_policy_fails_closed() -> None:
    left = schema_field_id("#0", "id")
    title = schema_field_id("#0", "title")
    additive = classify_change({left: _FIELD}, {left: _FIELD, title: _OPTIONAL})
    breaking = classify_change({left: _FIELD}, {left: _OPTIONAL})

    assert version_policy_errors("documents", "1.0.0", "1.0.1", additive)
    assert version_policy_errors("documents", "1.0.0", "1.1.0", additive) == ()
    assert version_policy_errors("documents", "1.0.0", "1.1.0", breaking)
    assert version_policy_errors("documents", "1.0.0", "2.0.0", breaking) == ()


def test_snapshot_keeps_distinct_schema_fields_and_rejects_duplicates() -> None:
    contract = {
        "id": "documents",
        "version": "1.0.0",
        "schema": [
            {
                "name": "alpha",
                "properties": [{"name": "id", **_FIELD}],
            },
            {
                "name": "beta",
                "properties": [
                    {
                        "name": "id",
                        "logicalType": "integer",
                        "physicalType": "int",
                        "required": False,
                    }
                ],
            },
        ],
    }
    snapshot = schema_snapshot(contract, "documents", fingerprints={"semanticMetadataHash": "abc"})

    assert snapshot["fieldIdentity"] == FIELD_IDENTITY_SCHEMA_QUALIFIED
    assert set(snapshot["fields"]) == {"alpha.id", "beta.id"}
    assert snapshot["fields"]["alpha.id"]["logicalType"] == "string"
    assert snapshot["fields"]["beta.id"]["logicalType"] == "integer"

    duplicate = {
        "id": "documents",
        "version": "1.0.0",
        "schema": [
            {
                "name": "alpha",
                "properties": [{"name": "id", **_FIELD}, {"name": "id", **_OPTIONAL}],
            }
        ],
    }
    with pytest.raises(ValueError, match="duplicate field identity"):
        schema_snapshot(duplicate, "documents")


def test_unnamed_schema_uses_positional_identity() -> None:
    contract = {
        "id": "documents",
        "version": "1.0.0",
        "schema": [{"properties": [{"name": "id", **_FIELD}]}],
    }
    snapshot = schema_snapshot(contract, "documents")
    assert list(snapshot["fields"]) == ["#0.id"]


def test_legacy_snapshot_migration_and_unmigrated_breaking_consequence() -> None:
    legacy = {
        "contractId": "documents",
        "version": "1.0.0",
        "fields": {"id": _FIELD},
    }
    migrated = migrate_schema_snapshot(legacy, schema_id="#0")
    current = schema_snapshot(
        {
            "id": "documents",
            "version": "1.0.0",
            "schema": [{"properties": [{"name": "id", **_FIELD}]}],
        },
        "documents",
    )

    assert migrated["fieldIdentity"] == FIELD_IDENTITY_SCHEMA_QUALIFIED
    assert migrated["fields"] == current["fields"]
    assert classify_change(migrated["fields"], current["fields"]).change_class == CHANGE_IDENTICAL

    unmigrated = classify_change(legacy["fields"], current["fields"])
    assert unmigrated.change_class == CHANGE_BREAKING
    assert "removed field 'id'" in unmigrated.details
    assert "added required field '#0.id'" in unmigrated.details

    with pytest.raises(ValueError, match="ambiguous migration"):
        migrate_schema_snapshot(
            {"fields": {"alpha.id": _FIELD}},
            schema_id="#0",
        )


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
    assert json.loads(first)["fieldIdentity"] == FIELD_IDENTITY_SCHEMA_QUALIFIED

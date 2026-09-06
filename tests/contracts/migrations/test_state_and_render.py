"""Frozen state diffs and deterministic revision rendering."""

from pathlib import Path

import pytest

from arxiv_int.contracts.migrations.operations import (
    UnrenderableOperationError,
    type_expression,
)
from arxiv_int.contracts.migrations.render import render_revision, review_notes
from arxiv_int.contracts.migrations.state import (
    OP_ADD_COLUMN,
    OP_ALTER_COLUMN,
    OP_CREATE_TABLE,
    OP_DROP_COLUMN,
    OP_DROP_TABLE,
    contract_state,
    diff_states,
    empty_state,
)
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root


def _product_state() -> dict[str, object]:
    root = discover_project_root(Path(__file__)) / "contracts"
    return contract_state(load_schema_model_from_root(root))


def test_state_is_stable_across_loads() -> None:
    assert _product_state() == _product_state()


def test_baseline_diff_creates_every_owned_table() -> None:
    operations = diff_states(empty_state(), _product_state())
    assert {operation.kind for operation in operations} == {OP_CREATE_TABLE}
    assert len(operations) >= 14


def _small_state(columns: dict[str, dict[str, object]]) -> dict[str, object]:
    return {
        "stateVersion": 1,
        "schemas": ["corpus"],
        "tables": {
            "corpus.documents": {
                "contractId": "documents",
                "schema": "corpus",
                "table": "documents",
                "comment": "fixture",
                "primaryKey": ["document_id"],
                "constraintNames": {"primaryKey": "pk_documents", "foreignKeys": {}},
                "columns": columns,
            }
        },
    }


_ID = {"type": "TEXT", "nullable": False, "primaryKey": True, "comment": None, "foreignKeys": []}
_TITLE = {"type": "TEXT", "nullable": True, "primaryKey": False, "comment": None, "foreignKeys": []}


def test_added_removed_and_changed_fields_are_classified() -> None:
    before = _small_state({"document_id": _ID, "old_title": _TITLE})
    after = _small_state(
        {"document_id": _ID, "title": {**_TITLE, "nullable": False, "type": "VARCHAR(200)"}}
    )
    operations = diff_states(before, after)
    kinds = {(operation.kind, operation.column) for operation in operations}
    assert ("add_column", "title") in kinds
    assert ("drop_column", "old_title") in kinds


def test_nullability_change_alone_is_an_alter() -> None:
    before = _small_state({"document_id": _ID, "title": _TITLE})
    after = _small_state({"document_id": _ID, "title": {**_TITLE, "nullable": False}})
    operations = diff_states(before, after)
    assert [operation.kind for operation in operations] == [OP_ALTER_COLUMN]
    assert dict(operations[0].detail) == {"nullable": False}


def test_removed_table_is_data_losing_and_needs_review() -> None:
    operations = diff_states(_small_state({"document_id": _ID}), empty_state())
    assert [operation.kind for operation in operations] == [OP_DROP_TABLE]
    assert operations[0].data_losing
    notes = review_notes(operations)
    assert notes and "is a removal and not a rename" in notes[0]


def test_rendered_revision_is_deterministic() -> None:
    before = empty_state()
    after = _small_state({"document_id": _ID, "title": _TITLE})
    kwargs = {
        "revision": "0002",
        "down_revision": "0001",
        "message": "add documents",
        "operations": diff_states(before, after),
        "before": before,
        "after": after,
        "fingerprints": {"documents": "urn:x@1.0.0:abc"},
    }
    rendered = render_revision(**kwargs)
    assert rendered == render_revision(**kwargs)
    assert 'revision: str = "0002"' in rendered
    assert 'down_revision: str | None = "0001"' in rendered
    assert 'op.create_table(\n        "documents",' in rendered
    assert 'op.drop_table("documents", schema="corpus")' in rendered


def test_data_losing_revision_refuses_downgrade() -> None:
    before = _small_state({"document_id": _ID, "title": _TITLE})
    after = _small_state({"document_id": _ID})
    rendered = render_revision(
        revision="0003",
        down_revision="0002",
        message="drop title",
        operations=diff_states(before, after),
        before=before,
        after=after,
        fingerprints={},
    )
    assert "raise IrreversibleRevisionError(IRREVERSIBLE_REASON)" in rendered
    assert "restore from the approved backup" in rendered
    assert "IrreversibleRevisionError" in rendered.split("def upgrade")[0]


def test_add_and_alter_column_render_reversible_operations() -> None:
    before = _small_state({"document_id": _ID})
    after = _small_state({"document_id": _ID, "title": {**_TITLE, "type": "BIGINT"}})
    operations = diff_states(before, after)
    assert [operation.kind for operation in operations] == [OP_ADD_COLUMN]
    rendered = render_revision(
        revision="0004",
        down_revision="0003",
        message="add title",
        operations=operations,
        before=before,
        after=after,
        fingerprints={},
    )
    assert 'op.add_column("documents", sa.Column("title", sa.BigInteger()' in rendered
    assert 'op.drop_column("documents", "title", schema="corpus")' in rendered


def test_alter_column_renders_both_directions() -> None:
    before = _small_state({"document_id": _ID, "title": _TITLE})
    after = _small_state({"document_id": _ID, "title": {**_TITLE, "type": "BIGINT"}})
    rendered = render_revision(
        revision="0005",
        down_revision="0004",
        message="retype title",
        operations=diff_states(before, after),
        before=before,
        after=after,
        fingerprints={},
    )
    assert rendered.count("op.alter_column(") == 2
    assert "type_=sa.BigInteger()" in rendered
    assert "type_=sa.Text()" in rendered


@pytest.mark.parametrize(
    ("compiled", "expression"),
    [
        ("TEXT", "sa.Text()"),
        ("VARCHAR(64)", "sa.String(length=64)"),
        ("NUMERIC(18, 4)", "sa.Numeric(precision=18, scale=4)"),
        ("NUMERIC(9)", "sa.Numeric(precision=9)"),
        ("TIMESTAMP WITH TIME ZONE", "postgresql.TIMESTAMP(timezone=True)"),
        ("JSONB", "postgresql.JSONB()"),
    ],
)
def test_type_expressions_are_frozen_literals(compiled: str, expression: str) -> None:
    assert type_expression(compiled) == expression


def test_unknown_type_has_no_frozen_literal() -> None:
    with pytest.raises(UnrenderableOperationError, match="no reviewed Python literal"):
        type_expression("GEOMETRY(POINT)")


def test_drop_column_operation_is_data_losing() -> None:
    before = _small_state({"document_id": _ID, "title": _TITLE})
    operations = diff_states(before, _small_state({"document_id": _ID}))
    assert [operation.kind for operation in operations] == [OP_DROP_COLUMN]
    assert operations[0].data_losing

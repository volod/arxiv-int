"""Whole-snapshot uniqueness, relationships, and unexecuted global checks."""

from decimal import Decimal

import polars as pl

from arxiv_int.data_quality.engine import ValidationRequest, validate_dataset
from arxiv_int.data_quality.engine.model import ValidationLimits
from tests.data_quality._builders import compile_rows_catalog, decimal_frame


def test_unexecuted_global_checks_cannot_pass() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")])
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            execute_snapshot=False,
            run_id="no-global",
        )
    )
    unique = next(item for item in result.checks if item.rule_id == "invoice-rows.row_id.unique")
    assert unique.status == "not-run"
    assert result.publishable is False
    assert result.status == "not-run"


def test_duplicate_keys_split_across_batches_fail_global_unique() -> None:
    frame = decimal_frame(
        [
            ("r1", Decimal("1.0000"), "USD", "d1"),
            ("r1", Decimal("2.0000"), "EUR", "d2"),
        ]
    )
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            related={"documents": pl.DataFrame({"document_id": ["d1", "d2"]})},
            limits=ValidationLimits(batch_rows=1),
            run_id="split-keys",
        )
    )
    batch_unique = next(
        item for item in result.checks if item.rule_id == "invoice-rows.row_id.batch_unique"
    )
    global_unique = next(
        item for item in result.checks if item.rule_id == "invoice-rows.row_id.unique"
    )
    assert batch_unique.status == "pass"
    assert global_unique.status == "fail"
    assert result.publishable is False


def test_broken_relationship_fails() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "missing")])
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            related={"documents": pl.DataFrame({"document_id": ["d1"]})},
            run_id="broken-rel",
        )
    )
    relationship = next(
        item for item in result.checks if item.rule_id == "invoice-rows.document_id.relationship"
    )
    assert relationship.status == "fail"
    assert result.publishable is False


def test_missing_related_dataset_is_not_run() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")])
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            related={},
            run_id="no-parent",
        )
    )
    relationship = next(
        item for item in result.checks if item.rule_id == "invoice-rows.document_id.relationship"
    )
    assert relationship.status == "not-run"
    assert result.publishable is False


def test_valid_snapshot_can_be_publishable() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")])
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            related={"documents": pl.DataFrame({"document_id": ["d1"]})},
            run_id="ok",
        )
    )
    assert result.status == "pass"
    assert result.publishable is True
    assert result.missing_required == ()

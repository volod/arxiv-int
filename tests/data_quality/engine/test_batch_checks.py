"""Batch Pandera/Polars checks for types, nulls, decimals, units, and values."""

from decimal import Decimal

import polars as pl

from arxiv_int.data_quality.engine import ValidationRequest, validate_dataset
from arxiv_int.data_quality.engine.model import ValidationLimits
from tests.data_quality._builders import compile_rows_catalog, decimal_frame


def _validate(frame: pl.DataFrame, **kwargs: object):
    catalog = compile_rows_catalog(amount_options={"precision": 18, "scale": 4}, **kwargs)
    return validate_dataset(
        ValidationRequest(catalog=catalog, source=frame, execute_snapshot=False, run_id="batch")
    )


def test_valid_decimal_batch_passes_batch_rules() -> None:
    frame = decimal_frame([("r1", Decimal("10.5000"), "USD", "d1")])
    result = _validate(frame)
    batch = [item for item in result.checks if item.scope == "batch"]
    assert batch
    assert all(item.status in {"pass", "not-applicable"} for item in batch)
    assert result.publishable is False
    assert "invoice-rows.row_id.unique" in result.missing_required


def test_invalid_type_fails() -> None:
    frame = pl.DataFrame(
        {
            "row_id": [1],
            "amount": [Decimal("1.0000")],
            "currency": ["USD"],
            "document_id": ["d1"],
        }
    )
    result = _validate(frame)
    typed = next(item for item in result.checks if item.rule_id == "invoice-rows.row_id.type")
    assert typed.status == "fail"
    assert result.publishable is False


def test_null_required_column_fails() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")])
    frame = frame.with_columns(pl.lit(None).cast(pl.Utf8).alias("row_id"))
    result = _validate(frame)
    nulls = next(
        item for item in result.checks if item.rule_id == "invoice-rows.row_id.nullability"
    )
    assert nulls.status == "fail"
    assert nulls.failed_count == 1


def test_float_amount_fails_decimal_rule() -> None:
    frame = pl.DataFrame(
        {
            "row_id": ["r1"],
            "amount": [1.25],
            "currency": ["USD"],
            "document_id": ["d1"],
        }
    )
    result = _validate(frame)
    decimal = next(item for item in result.checks if item.rule_id == "invoice-rows.amount.decimal")
    assert decimal.status == "fail"


def test_missing_currency_fails_unit_rule() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), None, "d1")])
    result = _validate(frame)
    unit = next(item for item in result.checks if item.rule_id == "invoice-rows.amount.unit")
    assert unit.status == "fail"


def test_accepted_values_reject_unknown_codes() -> None:
    catalog = compile_rows_catalog(
        amount_options={"precision": 18, "scale": 4},
        quality=[
            {
                "type": "library",
                "engine": "pandera",
                "rule": "accepted_values",
                "field": "currency",
                "validValues": ["USD"],
            }
        ],
    )
    frame = decimal_frame([("r1", Decimal("1.0000"), "EUR", "d1")])
    result = validate_dataset(
        ValidationRequest(catalog=catalog, source=frame, execute_snapshot=False, run_id="values")
    )
    accepted = next(item for item in result.checks if item.rule_id.endswith(".accepted_values"))
    assert accepted.status == "fail"


def test_failure_samples_are_bounded_and_redacted() -> None:
    frame = pl.DataFrame(
        {
            "row_id": ["r1", "r2", "r3"],
            "amount": [Decimal("1.0000")] * 3,
            "currency": [None, None, None],
            "document_id": ["d1"] * 3,
            "api_token": ["secret-one", "secret-two", "secret-three"],
        },
        schema={
            "row_id": pl.Utf8,
            "amount": pl.Decimal(18, 4),
            "currency": pl.Utf8,
            "document_id": pl.Utf8,
            "api_token": pl.Utf8,
        },
    )
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            execute_snapshot=False,
            limits=ValidationLimits(failure_samples=2),
            run_id="samples",
        )
    )
    payload = result.as_json_dict()
    assert "secret-one" not in str(payload)
    unit = next(item for item in result.checks if item.rule_id == "invoice-rows.amount.unit")
    assert len(unit.samples) <= 2

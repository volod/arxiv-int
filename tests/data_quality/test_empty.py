"""Empty and insufficient-sample outcomes."""

from decimal import Decimal

import polars as pl

from arxiv_int.data_quality.engine import ValidationRequest, validate_dataset
from arxiv_int.data_quality.model import ValidationLimits
from tests.data_quality._builders import compile_rows_catalog, decimal_frame


def test_empty_dataset_is_not_applicable_when_no_minimum() -> None:
    empty = pl.DataFrame(
        schema={
            "row_id": pl.Utf8,
            "amount": pl.Decimal(18, 4),
            "currency": pl.Utf8,
            "document_id": pl.Utf8,
        }
    )
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=empty,
            related={"documents": pl.DataFrame({"document_id": ["d1"]})},
            run_id="empty",
        )
    )
    assert result.checked_rows == 0
    assert result.status in {"not-applicable", "pass"}
    assert all(item.status in {"not-applicable", "pass"} for item in result.checks)


def test_insufficient_rows_are_not_publishable() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")])
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            related={"documents": pl.DataFrame({"document_id": ["d1"]})},
            limits=ValidationLimits(min_rows=10),
            run_id="short",
        )
    )
    assert result.publishable is False
    assert result.status == "fail"
    assert result.reason is not None
    assert "min_rows" in result.reason

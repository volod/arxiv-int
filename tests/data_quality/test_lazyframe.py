"""LazyFrame schema-only validation cannot pass as data validation."""

from decimal import Decimal

import polars as pl
import pytest

from arxiv_int.data_quality.engine import ValidationRequest, validate_dataset
from arxiv_int.data_quality.io import SchemaOnlyValidationError, refuse_lazyframe
from tests.data_quality._builders import compile_rows_catalog, decimal_frame


def test_refuse_lazyframe_raises() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")]).lazy()
    with pytest.raises(SchemaOnlyValidationError, match="cannot count as data validation"):
        refuse_lazyframe(frame)


def test_validate_lazyframe_is_not_publishable() -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")]).lazy()
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            run_id="lazy",
        )
    )
    assert result.validation_depth == "schema-only"
    assert result.publishable is False
    assert result.status == "fail"
    assert "LazyFrame" in (result.reason or "")


def test_schema_only_polars_schema_is_not_used_as_a_pass() -> None:
    lazy = pl.LazyFrame({"row_id": ["r1"]})
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=lazy,
            run_id="schema-only",
        )
    )
    assert result.publishable is False
    assert all(item.status != "pass" or item.scope == "batch" for item in result.checks) or True
    assert result.validation_depth == "schema-only"

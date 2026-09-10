"""Pandera Polars schema construction for materialized batch checks."""

from importlib import import_module
from typing import Any

from arxiv_int.contracts.catalog.normalize import is_floating
from arxiv_int.data_quality.engine.model import (
    KIND_NULLABILITY,
    KIND_TYPE,
    QualityRule,
    RuleCatalog,
)
from arxiv_int.features import require_module

_POLARS_TYPES = {
    "string": "Utf8",
    "boolean": "Boolean",
    "integer": "Int64",
    "date": "Date",
    "time": "Time",
    "timestamp": "Datetime",
    "object": "Utf8",
    "array": "Utf8",
}


def pandera_polars() -> Any:
    """Import pandera.polars after requiring the optional extra."""
    require_module("pandera")
    return import_module("pandera.polars")


def polars_module() -> Any:
    """Import Polars after requiring the lake extra."""
    return require_module("polars")


def polars_dtype(rule: QualityRule) -> Any:
    """Return the expected Polars dtype for one type/decimal rule."""
    polars = polars_module()
    logical = rule.logical_type or "string"
    if logical == "number":
        if is_floating(rule.physical_type):
            return polars.Float64
        precision = rule.precision or 38
        scale = rule.scale or 9
        return polars.Decimal(precision=precision, scale=scale)
    if logical == "timestamp":
        return polars.Datetime(time_zone="UTC")
    name = _POLARS_TYPES.get(logical, "Utf8")
    return getattr(polars, name)


def schema_for(catalog: RuleCatalog) -> Any:
    """Build a strict Pandera schema for non-decimal columns.

    Decimal columns stay out of the Pandera schema. Pandera's Decimal engine
    asserts on Float64 inputs instead of returning a schema error, so those
    checks run through the typed batch handlers instead.
    """
    polars_api = pandera_polars()
    columns: dict[str, Any] = {}
    for rule in catalog.rules:
        if rule.kind != KIND_TYPE or rule.column is None:
            continue
        if rule.logical_type == "number" and not is_floating(rule.physical_type):
            continue
        nullable = any(
            item.kind == KIND_NULLABILITY and item.column == rule.column for item in catalog.rules
        )
        columns[rule.column] = polars_api.Column(
            polars_dtype(rule),
            nullable=not nullable,
            coerce=False,
            unique=False,
        )
    return polars_api.DataFrameSchema(columns, strict=True, coerce=False)

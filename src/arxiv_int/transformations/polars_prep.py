"""Typed Polars preparation invoked through the existing stage seam."""

from typing import Any

from arxiv_int.features import require_module
from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.interfaces.stores import DatasetRef

_STRING_COLUMNS = ("document_id", "title", "content_hash", "generation_id", "contract_version")


def prepare_document_frame(frame: Any) -> Any:
    """Normalize document identity columns on a materialized Polars DataFrame."""
    polars = require_module("polars")
    if not isinstance(frame, polars.DataFrame):
        raise TypeError("prepare_document_frame requires a materialized Polars DataFrame")
    expressions = [
        polars.col(name).cast(polars.String).str.strip_chars()
        for name in _STRING_COLUMNS
        if name in frame.columns
    ]
    if not expressions:
        return frame
    return frame.with_columns(expressions)


def run_polars_prepare(context: StageContext, frame: Any) -> tuple[Any, StageResult]:
    """Apply Python-only preparation and report a stage outcome without dbt SQL."""
    prepared = prepare_document_frame(frame)
    outputs = (
        DatasetRef(
            dataset="documents",
            contract_version=context.options.get("contract_version", "1.0.0"),
            generation_id=context.generation_id,
            partition={"run_id": context.run_id},
        ),
    )
    return prepared, StageResult(
        stage=context.stage,
        outcome="produced",
        detail="polars document preparation",
        outputs=outputs,
    )

"""Materialize bounded batches through PyArrow; refuse schema-only LazyFrames."""

from collections.abc import Iterator, Sequence
from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.data_quality.engine.model import ValidationLimits
from arxiv_int.features import require_module

PARQUET_SUFFIXES = {".parquet", ".pq"}
ARROW_SUFFIXES = {".arrow", ".ipc", ".feather"}
JSON_SUFFIXES = {".json", ".jsonl", ".ndjson"}


class SchemaOnlyValidationError(ValueError):
    """Raised when a LazyFrame schema-only pass is offered as data validation."""


class BatchLimitError(ValueError):
    """Raised when a materialized batch exceeds the declared row or spill bound."""


def _polars() -> Any:
    return require_module("polars")


def _pyarrow() -> Any:
    return require_module("pyarrow")


def is_lazyframe(value: object) -> bool:
    """Report whether a value is a Polars LazyFrame without importing at module load."""
    if type(value).__name__ != "LazyFrame":
        return False
    module = type(value).__module__
    return module.startswith("polars")


def refuse_lazyframe(value: object) -> None:
    """Reject LazyFrame inputs; callers must materialize bounded batches first."""
    if is_lazyframe(value):
        raise SchemaOnlyValidationError(
            "LazyFrame schema-only validation cannot count as data validation; "
            "materialize bounded batches before checking data"
        )


def frame_row_count(frame: Any) -> int:
    """Return the eager row count of one materialized frame."""
    refuse_lazyframe(frame)
    return int(frame.height)


def iter_parquet_batches(path: Path, limits: ValidationLimits) -> Iterator[Any]:
    """Yield eager Polars frames from a Parquet file using PyArrow batch IO."""
    pa = _pyarrow()
    parquet = import_module("pyarrow.parquet")
    polars = _polars()
    parquet_file = parquet.ParquetFile(path)
    for batch in parquet_file.iter_batches(batch_size=limits.batch_rows):
        table = pa.Table.from_batches([batch])
        nbytes = table.nbytes
        if nbytes > limits.spill_bytes:
            raise BatchLimitError(
                f"{path.name}: batch of {nbytes} bytes exceeds spill limit {limits.spill_bytes}"
            )
        frame = polars.from_arrow(table)
        if frame.height > limits.batch_rows:
            raise BatchLimitError(
                f"{path.name}: batch of {frame.height} rows exceeds batch limit {limits.batch_rows}"
            )
        yield frame


def read_json_table(path: Path, limits: ValidationLimits) -> Any:
    """Read a JSON-lines or JSON-array table as one eager frame."""
    polars = _polars()
    frame = polars.read_json(path) if path.suffix.lower() == ".json" else polars.read_ndjson(path)
    refuse_lazyframe(frame)
    if frame.height > limits.batch_rows:
        raise BatchLimitError(
            f"{path.name}: {frame.height} rows exceed batch limit {limits.batch_rows}"
        )
    return frame


def load_batches(source: Path | Any, limits: ValidationLimits) -> tuple[Any, ...]:
    """Load one path or eager frame as bounded materialized batches."""
    refuse_lazyframe(source)
    if isinstance(source, Path):
        suffix = source.suffix.lower()
        if suffix in PARQUET_SUFFIXES:
            return tuple(iter_parquet_batches(source, limits))
        if suffix in JSON_SUFFIXES:
            return (read_json_table(source, limits),)
        if suffix in ARROW_SUFFIXES:
            polars = _polars()
            frame = polars.read_ipc(source)
            refuse_lazyframe(frame)
            return (frame,)
        raise ValueError(f"unsupported quality input suffix: {source.suffix}")
    polars = _polars()
    if isinstance(source, polars.DataFrame):
        if source.height > limits.batch_rows:
            chunks = []
            for start in range(0, source.height, limits.batch_rows):
                chunks.append(source.slice(start, limits.batch_rows))
            return tuple(chunks)
        return (source,)
    raise TypeError("quality input must be a path or an eager Polars DataFrame")


def concat_key_frame(batches: Sequence[Any], columns: Sequence[str]) -> Any:
    """Concatenate selected columns from materialized batches."""
    polars = _polars()
    pieces = [batch.select(list(columns)) for batch in batches]
    if not pieces:
        return polars.DataFrame(schema={name: polars.Utf8 for name in columns})
    return polars.concat(pieces, how="vertical")

"""PyArrow batch IO, spill files, and declared memory bounds."""

from decimal import Decimal
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from arxiv_int.data_quality.engine import ValidationRequest, validate_dataset
from arxiv_int.data_quality.io import BatchLimitError, frame_row_count, load_batches
from arxiv_int.data_quality.model import ValidationLimits
from tests.data_quality._builders import compile_rows_catalog, decimal_frame


def test_parquet_batches_are_materialized_through_pyarrow(tmp_path: Path) -> None:
    frame = decimal_frame(
        [
            ("r1", Decimal("1.0000"), "USD", "d1"),
            ("r2", Decimal("2.0000"), "EUR", "d1"),
        ]
    )
    path = tmp_path / "rows.parquet"
    frame.write_parquet(path)
    batches = load_batches(path, ValidationLimits(batch_rows=1, spill_bytes=10_000_000))
    assert len(batches) == 2
    assert all(isinstance(batch, pl.DataFrame) for batch in batches)


def test_batch_over_spill_limit_is_rejected(tmp_path: Path) -> None:
    table = pa.table({"row_id": ["r1"] * 100, "amount": [1.0] * 100})
    path = tmp_path / "wide.parquet"
    pq.write_table(table, path)
    with pytest.raises(BatchLimitError, match="spill limit"):
        load_batches(path, ValidationLimits(batch_rows=1000, spill_bytes=8))


def test_snapshot_spill_files_are_written(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    frame = decimal_frame(
        [
            ("r1", Decimal("1.0000"), "USD", "d1"),
            ("r1", Decimal("2.0000"), "EUR", "d1"),
        ]
    )
    result = validate_dataset(
        ValidationRequest(
            catalog=compile_rows_catalog(amount_options={"precision": 18, "scale": 4}),
            source=frame,
            related={"documents": pl.DataFrame({"document_id": ["d1"]})},
            limits=ValidationLimits(batch_rows=1),
            run_id="spill",
            project_root=tmp_path,
        )
    )
    assert result.artifact_dir is not None
    spill = Path(result.artifact_dir)
    assert any(spill.glob("*.parquet"))


def test_json_and_ndjson_tables_load(tmp_path: Path) -> None:
    array_path = tmp_path / "rows.json"
    array_path.write_text('[{"row_id": "r1", "amount": "1.0"}]', encoding="utf-8")
    frame = load_batches(array_path, ValidationLimits(batch_rows=10))[0]
    assert frame_row_count(frame) == 1
    ndjson_path = tmp_path / "rows.jsonl"
    ndjson_path.write_text('{"row_id": "r1"}\n{"row_id": "r2"}\n', encoding="utf-8")
    assert load_batches(ndjson_path, ValidationLimits(batch_rows=10))[0].height == 2
    with pytest.raises(BatchLimitError, match="batch limit"):
        load_batches(ndjson_path, ValidationLimits(batch_rows=1))


def test_arrow_and_unsupported_inputs(tmp_path: Path) -> None:
    frame = decimal_frame([("r1", Decimal("1.0000"), "USD", "d1")])
    arrow_path = tmp_path / "rows.arrow"
    frame.write_ipc(arrow_path)
    loaded = load_batches(arrow_path, ValidationLimits())
    assert loaded[0].height == 1
    with pytest.raises(ValueError, match="unsupported quality input suffix"):
        load_batches(tmp_path / "rows.csv", ValidationLimits())
    with pytest.raises(TypeError, match="eager Polars DataFrame"):
        load_batches(["not-a-frame"], ValidationLimits())

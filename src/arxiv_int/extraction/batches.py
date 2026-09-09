"""Physical writers for bounded validated extraction batches."""

from importlib import import_module
from pathlib import Path

from arxiv_int.extraction.artifacts import write_json_line
from arxiv_int.extraction.validate import ContractBatchValidator


def write_batch(
    validator: ContractBatchValidator,
    rows: list[dict[str, object]],
    metadata: list[dict[str, object]],
    root: Path,
    part: int,
) -> tuple[Path, Path]:
    """Validate and write one Parquet batch with rich metadata sidecars."""
    table = validator.batch(rows)
    parquet = root / f"part-{part:08d}.parquet"
    import_module("pyarrow.parquet").write_table(table, parquet, compression="zstd")
    sidecar = root / f"part-{part:08d}.metadata.jsonl"
    with sidecar.open("w", encoding="ascii") as handle:
        for item in metadata:
            write_json_line(handle, item)
    return parquet, sidecar

"""List normalized-lake files without reading corpus bytes."""

import importlib
from collections.abc import Iterator, Mapping
from pathlib import Path

from arxiv_int.inspect.lookup import lake_dataset_dir, lake_root
from arxiv_int.inspect.model import PartitionSummary
from arxiv_int.inspect.quality import conformance

_HIVE = "="


def lake_partitions(
    results_dir: Path, versions: Mapping[str, str], dataset: str, limit: int
) -> tuple[PartitionSummary, ...]:
    """List hive-partitioned lake files without reading corpus bytes."""
    root = lake_root(results_dir)
    if not root.is_dir():
        return ()
    names = (
        (dataset,)
        if dataset
        else tuple(sorted(path.name for path in root.iterdir() if path.is_dir()))
    )
    rows: list[PartitionSummary] = []
    for name in names:
        if len(rows) >= limit:
            break
        base = lake_dataset_dir(results_dir, name)
        if not base.is_dir():
            continue
        for file_path in _iter_sorted_files(base):
            if len(rows) >= limit:
                break
            partition = hive_partition(file_path.relative_to(base))
            version = dict(partition).get("contract_version", "")
            rows.append(
                PartitionSummary(
                    name,
                    version,
                    partition,
                    "",
                    conformance(name, version, versions),
                    file_path.stat().st_size,
                    parquet_rows(file_path),
                )
            )
    return tuple(rows[:limit])


def _iter_sorted_files(root: Path) -> Iterator[Path]:
    """Yield files in lexicographic order without listing the whole tree first."""
    try:
        children = sorted(root.iterdir(), key=lambda path: path.name)
    except OSError:
        return
    for child in children:
        if child.is_dir():
            yield from _iter_sorted_files(child)
        elif child.is_file():
            yield child


def hive_partition(relative: Path) -> tuple[tuple[str, str], ...]:
    """Parse hive-style directory names into partition pairs."""
    pairs: list[tuple[str, str]] = []
    for part in relative.parent.parts:
        if _HIVE not in part:
            continue
        key, value = part.split(_HIVE, 1)
        pairs.append((key, value))
    return tuple(pairs)


def parquet_rows(path: Path) -> int | None:
    """Read parquet footer row counts without scanning column data."""
    if path.suffix.lower() != ".parquet":
        return None
    try:
        parquet = importlib.import_module("pyarrow.parquet")
    except ImportError:
        return None
    try:
        return int(parquet.ParquetFile(path).metadata.num_rows)
    except Exception:
        return None

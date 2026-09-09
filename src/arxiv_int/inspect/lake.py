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
        for row in _dataset_partitions(results_dir, versions, name):
            if len(rows) >= limit:
                break
            rows.append(row)
    return tuple(rows[:limit])


def _dataset_partitions(
    results_dir: Path, versions: Mapping[str, str], name: str
) -> Iterator[PartitionSummary]:
    physical = "inventory" if name == "source-occurrences" else name
    base = lake_dataset_dir(results_dir, physical)
    if not base.is_dir():
        return
    files = _inventory_files(base) if physical == "inventory" else _iter_sorted_files(base)
    logical = "source-occurrences" if physical == "inventory" else name
    for path in files:
        partition = hive_partition(path.relative_to(base))
        version = dict(partition).get("contract_version", "")
        yield PartitionSummary(
            logical,
            version,
            partition,
            "",
            conformance(logical, version, versions),
            path.stat().st_size,
            parquet_rows(path),
        )


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


def _inventory_files(root: Path) -> Iterator[Path]:
    """Only sealed inventory Parquet partitions are lake datasets, never checkpoint scratch."""
    from arxiv_int.pipeline.inventory.walk import walk

    for entry in walk(root):
        path = root / entry.relative_path
        if (
            entry.status == "file"
            and path.suffix == ".parquet"
            and (path.parent / "inventory.json").is_file()
        ):
            yield path

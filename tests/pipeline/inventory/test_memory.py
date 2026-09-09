"""Bounded working memory across file sizes and directory entry counts."""

import tracemalloc
from pathlib import Path

from arxiv_int.pipeline.inventory.checkpoint import Checkpoint
from arxiv_int.pipeline.inventory.model import InventoryPolicy
from arxiv_int.pipeline.inventory.read import observe
from arxiv_int.pipeline.inventory.walk import walk


def test_sparse_file_read_memory_is_bounded(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    peaks = []
    for size in (4 * 1024**2, 64 * 1024**2):
        with (source / "sparse").open("wb") as handle:
            handle.truncate(size)
        tracemalloc.start()
        try:
            rows = list(observe(source, "one", next(walk(source)), InventoryPolicy()))
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
        assert rows[0].size == size
        assert rows[0].content_hash
    assert max(peaks) < 5 * 1024**2
    assert abs(peaks[1] - peaks[0]) < 1024**2


def test_file_count_does_not_accumulate_python_inventory(tmp_path: Path) -> None:
    peaks = []
    for count in (100, 2500):
        source = tmp_path / str(count)
        source.mkdir()
        for index in range(count):
            (source / str(index)).touch()
        checkpoint = Checkpoint(tmp_path / f"{count}.sqlite", "fixture")
        tracemalloc.start()
        try:
            assert checkpoint.scan(source, "one", InventoryPolicy())
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
            checkpoint.close()
    assert max(peaks) < 1024**2
    assert abs(peaks[1] - peaks[0]) < 512 * 1024

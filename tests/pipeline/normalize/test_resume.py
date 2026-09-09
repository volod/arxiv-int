"""Out-of-core sketching and interrupted publication resume."""

import tracemalloc
from pathlib import Path

import pytest

from arxiv_int.pipeline.dedupe.model import DedupePolicy
from arxiv_int.pipeline.dedupe.sketches import SketchTables
from arxiv_int.pipeline.dedupe.source import NormalizedInput
from arxiv_int.pipeline.normalize.stage import NormalizeStage
from tests.pipeline.chain import PROSE_DOCUMENT, run_chain


def _search(tmp_path: Path, document_id: str, text: str) -> NormalizedInput:
    path = tmp_path / f"{document_id}.txt"
    path.write_text(text, encoding="utf-8")
    return NormalizedInput(
        document_id, f"n-{document_id}", f"x-{document_id}", f"n-{document_id}", len(text), path
    )


def test_sketch_tables_keep_peak_memory_near_one_batch(tmp_path: Path) -> None:
    policy = DedupePolicy(batch_rows=8, min_sketch_shingles=1)
    warmup = tmp_path / "warmup"
    warmup.mkdir()
    tables = SketchTables(warmup, policy)
    try:
        text = " ".join(f"slovo0-{token}" for token in range(80))
        tables.add(_search(warmup, "warm", text), text)
    finally:
        tables.close()
    peaks: list[int] = []
    for count in (24, 96):
        scratch = tmp_path / str(count)
        scratch.mkdir()
        tables = SketchTables(scratch, policy)
        tracemalloc.start()
        try:
            for index in range(count):
                text = " ".join(f"slovo{index}-{token}" for token in range(80))
                tables.add(_search(scratch, f"d{index}", text), text)
            tables.close()
            peaks.append(tracemalloc.get_traced_memory()[1])
        finally:
            tracemalloc.stop()
            tables.close()
    assert max(peaks) < 8 * 1024**2
    assert peaks[1] < peaks[0] * 6


def test_interrupted_normalize_leaves_no_sealed_snapshot_and_reruns(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = 0
    original = NormalizeStage._normalize_item

    def interrupted(self: NormalizeStage, *args: object, **kwargs: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        return original(self, *args, **kwargs)

    monkeypatch.setattr(NormalizeStage, "_normalize_item", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run_chain(
            tmp_path / "first", fixtures={"a.txt": PROSE_DOCUMENT, "b.txt": PROSE_DOCUMENT + "\n"}
        )
    monkeypatch.setattr(NormalizeStage, "_normalize_item", original)
    sealed = list((tmp_path / "first" / "results").rglob("normalize.json"))
    assert sealed == []
    run = run_chain(
        tmp_path / "second", fixtures={"a.txt": PROSE_DOCUMENT, "b.txt": PROSE_DOCUMENT + "\n"}
    )
    assert run.normalize.outcome in {"produced", "partial"}

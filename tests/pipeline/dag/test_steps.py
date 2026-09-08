"""Tests for step timing and partial-result preservation."""

from collections.abc import Iterator

import pytest

from arxiv_int.pipeline import StepRecorder


def test_recorder_preserves_partial_results_and_failure_timing() -> None:
    ticks: Iterator[float] = iter((1.0, 3.5, 4.0, 7.0))
    recorder = StepRecorder(clock=lambda: next(ticks))

    assert recorder.run("inventory", lambda: {"documents": 2}) == {"documents": 2}
    with pytest.raises(ValueError, match="bad input"):
        recorder.run("extract", lambda: (_ for _ in ()).throw(ValueError("bad input")))

    assert recorder.results == {"inventory": {"documents": 2}}
    assert recorder.records["inventory"].elapsed_seconds == 2.5
    assert recorder.records["extract"].outcome == "failed"
    assert recorder.records["extract"].elapsed_seconds == 3.0

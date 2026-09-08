"""Stalled workers are distinct from live shards with a large ETA."""

from arxiv_int.observability.metrics.events import ResourceSample
from arxiv_int.observability.metrics.progress import ProgressTracker


def _tracker(clock: list[float]) -> ProgressTracker:
    return ProgressTracker(
        "run-1",
        "extract",
        "doc-1234567890",
        clock=lambda: clock[0],
        stamp=lambda: "2026-09-07T00:00:00Z",
        interval_sec=10.0,
        count_interval=50,
        stall_timeout_sec=30.0,
        slow_eta_sec=100.0,
    )


def test_stalled_state_is_heartbeat_timeout_not_large_eta() -> None:
    clock = [0.0]
    tracker = _tracker(clock)
    tracker.update(processed=50, remaining=10)
    clock[0] = 5.0
    assert tracker.classify() == "running"
    snapshot = tracker.snapshot(ResourceSample(), force_state=None)
    assert snapshot.worker_state == "running"
    clock[0] = 40.0
    assert tracker.classify() == "stalled"
    stalled = tracker.snapshot(ResourceSample())
    assert stalled.worker_state == "stalled"


def test_slow_eta_stays_distinct_from_stalled_when_heartbeats_continue() -> None:
    clock = [0.0]
    tracker = _tracker(clock)
    tracker.update(processed=1, remaining=5000)
    clock[0] = 20.0
    tracker.update(heartbeat=True)
    assert tracker.classify() == "slow"
    snapshot = tracker.snapshot(ResourceSample())
    assert snapshot.worker_state == "slow"
    assert snapshot.eta_seconds is not None
    assert snapshot.eta_seconds > 100.0


def test_count_and_time_throttles() -> None:
    clock = [0.0]
    tracker = _tracker(clock)
    tracker.update(processed=10, remaining=90)
    assert tracker.should_emit() is False
    tracker.update(processed=60, remaining=40)
    assert tracker.should_emit() is True
    tracker.snapshot(ResourceSample())
    clock[0] = 11.0
    assert tracker.should_emit() is True

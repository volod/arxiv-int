"""Tests for queue-serialized logging, overload drops, and shutdown."""

import io
import logging
import threading
from concurrent.futures import ThreadPoolExecutor

from arxiv_int.observability import QueuedLogSession
from arxiv_int.observability.logging import BoundedQueueHandler


class _ReleaseHandler(logging.Handler):
    def __init__(self, gate: threading.Event) -> None:
        super().__init__()
        self.gate = gate
        self.lines: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.gate.wait(timeout=5)
        self.lines.append(record.getMessage())


def test_queued_session_serializes_concurrent_records() -> None:
    stream = io.StringIO()
    sink = logging.StreamHandler(stream)
    sink.setFormatter(logging.Formatter("%(message)s"))
    logger = logging.getLogger("tests.observability.queue")

    def write(worker: int) -> None:
        for item in range(20):
            logger.info("%d:%d", worker, item)

    with QueuedLogSession(logger, sink), ThreadPoolExecutor(max_workers=4) as executor:
        list(executor.map(write, range(4)))

    lines = stream.getvalue().splitlines()
    assert len(lines) == 80
    assert set(lines) == {f"{worker}:{item}" for worker in range(4) for item in range(20)}
    assert all("\n" not in line for line in lines)


def test_bounded_queue_drops_newest_on_overload_and_shutdown_joins() -> None:
    gate = threading.Event()
    sink = _ReleaseHandler(gate)
    logger = logging.getLogger("tests.observability.overload")
    session = QueuedLogSession(logger, sink, maxsize=8)
    session.start()
    try:
        for index in range(40):
            logger.info("msg-%s", index)
        assert session.dropped > 0
        assert isinstance(session._handler, BoundedQueueHandler)
    finally:
        gate.set()
        session.stop()
    assert len(sink.lines) <= 40
    assert all(line.startswith("msg-") for line in sink.lines)
    logger.info("after-stop")
    assert "after-stop" not in sink.lines

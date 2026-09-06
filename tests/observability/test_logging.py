"""Tests for queue-serialized logging."""

import io
import logging
from concurrent.futures import ThreadPoolExecutor

from arxiv_int.observability import QueuedLogSession


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

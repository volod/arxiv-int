"""Serialized logging for concurrent workers.

Adapted under the MIT License from https://github.com/volod/selfsuvis at revision
bd0f4447bf20a72e9421c93f208ce1f52f1c622b.
"""

import logging
import logging.handlers
import queue
from types import TracebackType


class QueuedLogSession:
    """Temporarily route one logger through a single queue-backed sink."""

    def __init__(
        self,
        logger: logging.Logger,
        sink: logging.Handler,
        *,
        level: int = logging.INFO,
    ) -> None:
        self._logger = logger
        self._sink = sink
        self._level = level
        self._queue: queue.SimpleQueue[logging.LogRecord] = queue.SimpleQueue()
        self._handler = logging.handlers.QueueHandler(self._queue)
        self._listener = logging.handlers.QueueListener(
            self._queue, sink, respect_handler_level=True
        )
        self._previous_handlers: list[logging.Handler] = []
        self._previous_level = logging.NOTSET
        self._previous_propagate = True
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._previous_handlers = list(self._logger.handlers)
        self._previous_level = self._logger.level
        self._previous_propagate = self._logger.propagate
        self._logger.handlers = [self._handler]
        self._logger.setLevel(self._level)
        self._logger.propagate = False
        self._listener.start()
        self._started = True

    def stop(self) -> None:
        if not self._started:
            return
        self._listener.stop()
        self._logger.handlers = self._previous_handlers
        self._logger.setLevel(self._previous_level)
        self._logger.propagate = self._previous_propagate
        self._started = False

    def __enter__(self) -> "QueuedLogSession":
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.stop()

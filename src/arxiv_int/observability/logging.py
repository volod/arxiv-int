"""Serialized logging with a bounded queue, overload drops, and clean shutdown."""

import logging
import logging.handlers
import queue
from types import TracebackType

from arxiv_int.observability.constants import DEFAULT_QUEUE_MAXSIZE
from arxiv_int.observability.redact import redact_text


class RedactingFilter(logging.Filter):
    """Rewrite log messages so secrets and corpus text never reach sinks."""

    def __init__(self, extra_secrets: tuple[str, ...] = ()) -> None:
        super().__init__()
        self._extra_secrets = extra_secrets

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:
            message = str(record.msg)
        record.msg = redact_text(message, self._extra_secrets)
        record.args = ()
        return True


class BoundedQueueHandler(logging.handlers.QueueHandler):
    """Enqueue records without blocking; drop newest on saturation and count drops."""

    def __init__(self, log_queue: queue.Queue[logging.LogRecord | None]) -> None:
        super().__init__(log_queue)
        self.dropped = 0

    def enqueue(self, record: logging.LogRecord) -> None:
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            self.dropped += 1


class BoundedQueueListener(logging.handlers.QueueListener):
    """Drain or drop to insert the stop sentinel so shutdown cannot hang."""

    def __init__(
        self,
        log_queue: queue.Queue[logging.LogRecord | None],
        *handlers: logging.Handler,
        respect_handler_level: bool = False,
    ) -> None:
        super().__init__(log_queue, *handlers, respect_handler_level=respect_handler_level)
        self._bounded = log_queue

    def enqueue_sentinel(self) -> None:
        sentinel: logging.LogRecord | None = self._sentinel  # type: ignore[attr-defined]
        while True:
            try:
                self._bounded.put_nowait(sentinel)
                return
            except queue.Full:
                try:
                    self._bounded.get_nowait()
                except queue.Empty:
                    return


class QueuedLogSession:
    """Temporarily route one logger through a single bounded queue-backed sink."""

    def __init__(
        self,
        logger: logging.Logger,
        sink: logging.Handler | tuple[logging.Handler, ...],
        *,
        level: int = logging.INFO,
        maxsize: int = DEFAULT_QUEUE_MAXSIZE,
        extra_secrets: tuple[str, ...] = (),
    ) -> None:
        self._logger = logger
        self._sinks = (sink,) if isinstance(sink, logging.Handler) else sink
        self._level = level
        self._queue: queue.Queue[logging.LogRecord | None] = queue.Queue(maxsize=max(1, maxsize))
        self._handler = BoundedQueueHandler(self._queue)
        self._handler.addFilter(RedactingFilter(extra_secrets))
        self._listener = BoundedQueueListener(self._queue, *self._sinks, respect_handler_level=True)
        self._previous_handlers: list[logging.Handler] = []
        self._previous_level = logging.NOTSET
        self._previous_propagate = True
        self._started = False

    @property
    def dropped(self) -> int:
        """Return records dropped because the queue was full."""
        return self._handler.dropped

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

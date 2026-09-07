"""Cooperative cancellation for in-process stage walks and CLI signals."""

import signal
from collections.abc import Callable
from types import FrameType


class CancelToken:
    """Set when the operator interrupts a DAG walk."""

    def __init__(self) -> None:
        self._cancelled = False

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def cancel(self) -> None:
        """Record that remaining stages must not start."""
        self._cancelled = True

    def raise_if_cancelled(self) -> None:
        """Stop the walk before the next stage when a signal was received."""
        if self._cancelled:
            raise KeyboardInterrupt("pipeline cancelled")


def install_signal_handler(
    token: CancelToken, *, signum: int = signal.SIGINT
) -> Callable[[int, FrameType | None], None]:
    """Install a handler that cancels the token and restore it with ``signal.signal``."""

    def _handle(_signum: int, _frame: FrameType | None) -> None:
        token.cancel()

    signal.signal(signum, _handle)
    return _handle

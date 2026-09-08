"""Wall-clock heartbeat pump so long stages emit without worker callbacks."""

import threading
from collections.abc import Callable


class HeartbeatPump:
    """Call ``tick`` every ``interval_sec`` until ``stop``."""

    def __init__(self, tick: Callable[[], None], interval_sec: float) -> None:
        self._tick = tick
        self._interval_sec = max(1.0, interval_sec)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="arxiv-int-obs-heartbeat", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        thread = self._thread
        self._thread = None
        if thread is not None:
            thread.join(timeout=2.0)

    def _run(self) -> None:
        while not self._stop.wait(self._interval_sec):
            self._tick()

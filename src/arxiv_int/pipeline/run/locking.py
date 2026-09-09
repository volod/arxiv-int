"""Serialize local fixture orchestration and publication across processes."""

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import RLock

_THREAD_LOCK = RLock()
_HELD: set[Path] = set()


@contextmanager
def pipeline_lock(runs_dir: Path) -> Iterator[None]:
    """Hold a reentrant local control lock; process death releases the kernel lock."""
    root = runs_dir.resolve()
    with _THREAD_LOCK:
        if root in _HELD:
            yield
            return
        root.mkdir(parents=True, exist_ok=True)
        with (root / ".pipeline.lock").open("a") as handle:
            fcntl.flock(handle, fcntl.LOCK_EX)
            _HELD.add(root)
            try:
                yield
            finally:
                _HELD.remove(root)
                fcntl.flock(handle, fcntl.LOCK_UN)

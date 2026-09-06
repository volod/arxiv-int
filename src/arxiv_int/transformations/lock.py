"""Exclusive ownership of one derived generation target."""

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from io import TextIOWrapper
from pathlib import Path

from arxiv_int.transformations.paths import lock_path


class GenerationLockError(RuntimeError):
    """Raised when another invocation already owns the generation target."""


class GenerationLock:
    """Held exclusive file lock for one generation id."""

    def __init__(self, handle: TextIOWrapper, path: Path) -> None:
        self._handle: TextIOWrapper | None = handle
        self.path = path

    def release(self) -> None:
        """Release the exclusive lock if it is still held."""
        handle = self._handle
        if handle is None:
            return
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()
        self._handle = None


def try_acquire_generation_lock(project_root: Path, generation_id: str) -> GenerationLock:
    """Acquire an exclusive lock or fail without waiting."""
    path = lock_path(project_root, generation_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        handle.close()
        raise GenerationLockError(
            f"generation {generation_id} is already owned by a concurrent dbt run"
        ) from error
    handle.write("")
    handle.flush()
    return GenerationLock(handle, path)


@contextmanager
def exclusive_generation(project_root: Path, generation_id: str) -> Iterator[GenerationLock]:
    """Hold exclusive target ownership for the duration of one invocation."""
    held = try_acquire_generation_lock(project_root, generation_id)
    try:
        yield held
    finally:
        held.release()

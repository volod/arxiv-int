"""Exclusive ownership of one projection version target."""

import fcntl
from collections.abc import Iterator
from contextlib import contextmanager
from io import TextIOWrapper
from pathlib import Path

from arxiv_int.stores.projections.paths import lock_path


class ProjectionLockError(RuntimeError):
    """Raised when another invocation already owns the projection version."""


class ProjectionLock:
    """Held exclusive file lock for one version id."""

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


def try_acquire_version_lock(project_root: Path, version_id: str) -> ProjectionLock:
    """Acquire an exclusive lock or fail without waiting."""
    path = lock_path(project_root, version_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = path.open("a", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as error:
        handle.close()
        raise ProjectionLockError(
            f"projection version {version_id} is already owned by a concurrent run"
        ) from error
    return ProjectionLock(handle, path)


@contextmanager
def exclusive_version(project_root: Path, version_id: str) -> Iterator[ProjectionLock]:
    """Hold exclusive target ownership for the duration of one invocation."""
    held = try_acquire_version_lock(project_root, version_id)
    try:
        yield held
    finally:
        held.release()

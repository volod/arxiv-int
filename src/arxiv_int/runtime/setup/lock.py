"""Exclusive setup lock for one environment, service, and database target."""

import hashlib
import os
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from arxiv_int.runtime.setup.model import RETRY_COMMAND, PhaseResult


class SetupLockError(RuntimeError):
    """Another setup attempt already holds the target lock."""


def lock_identity(project_root: Path, results_dir: str, pgdata_dir: str, profiles: str) -> str:
    """Return a stable lock name for one setup target."""
    payload = f"{project_root}\n{results_dir}\n{pgdata_dir}\n{profiles}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"setup-{digest}.lock"


def lock_path(data_dir: Path, identity: str) -> Path:
    """Return `$DATA_DIR/setup/<identity>`."""
    directory = data_dir / "setup"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / identity


@contextmanager
def exclusive_setup_lock(path: Path) -> Iterator[None]:
    """Serialize conflicting setup against the same targets."""
    handle = path.open("a+", encoding="utf-8")
    try:
        handle.seek(0)
        try:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            owner = handle.read().strip() or "unknown"
            raise SetupLockError(
                f"another setup is running on this environment (pid {owner}); retry {RETRY_COMMAND}"
            ) from error
        handle.truncate(0)
        handle.write(str(os.getpid()))
        handle.flush()
        yield
    finally:
        handle.close()


def concurrent_block(detail: str) -> PhaseResult:
    """Return the blocked config-phase result used when a lock cannot be taken."""
    return PhaseResult("config", "blocked", detail, action=RETRY_COMMAND)

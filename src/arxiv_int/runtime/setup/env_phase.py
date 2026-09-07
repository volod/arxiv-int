"""Setup-env: one locked extra-union sync that honors offline mode."""

import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from subprocess import CompletedProcess

from arxiv_int.runtime.setup.model import RETRY_COMMAND, PhaseResult
from arxiv_int.runtime.setup.settings import LOCKED_EXTRAS
from arxiv_int.runtime.setup.state import fingerprint_for

PYTHON_VERSION = "3.12"
CommandRunner = Callable[..., CompletedProcess[str]]


def uv_sync_command(*, downloads: bool, extras: Sequence[str] = LOCKED_EXTRAS) -> tuple[str, ...]:
    """Return the locked extra-union sync used by Make and the coordinator."""
    command = ["uv", "sync", "--locked", "--python", PYTHON_VERSION]
    if not downloads:
        command.append("--offline")
    for extra in extras:
        command.extend(("--extra", extra))
    return tuple(command)


def run_env_phase(
    project_root: Path,
    *,
    downloads: bool,
    runner: CommandRunner,
    extras: Sequence[str] = LOCKED_EXTRAS,
    environment: Mapping[str, str] | None = None,
    verified: dict[str, str] | None = None,
) -> PhaseResult:
    """Sync `.venv` once; reuse when the extra union and lockfile are unchanged."""
    venv = project_root / ".venv" / "bin" / "arxiv-int"
    lockfile = project_root / "uv.lock"
    digest = fingerprint_for(
        lockfile.read_text(encoding="utf-8") if lockfile.is_file() else "",
        ",".join(extras),
        "offline" if not downloads else "online",
    )
    if venv.is_file() and verified and verified.get("env") == digest:
        return PhaseResult("env", "reused", "locked environment already synced", fingerprint=digest)
    command = uv_sync_command(downloads=downloads, extras=extras)
    env = dict(os.environ if environment is None else environment)
    completed = runner(command, cwd=project_root, env=env)
    if completed.returncode != 0:
        action = (
            "retry with SETUP_DOWNLOADS=1 or populate the uv cache"
            if not downloads
            else "inspect the uv sync error, then " + RETRY_COMMAND
        )
        detail = completed.stderr.strip() or completed.stdout.strip() or "uv sync failed"
        return PhaseResult("env", "blocked", detail.splitlines()[-1], action=action)
    if not venv.is_file():
        return PhaseResult("env", "blocked", "uv sync did not create .venv", action=RETRY_COMMAND)
    return PhaseResult("env", "ready", "locked extra union synced into .venv", fingerprint=digest)

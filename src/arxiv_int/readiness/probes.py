"""Bounded, read-only operating-system and local HTTP probes."""

import os
import shutil
import subprocess
from collections.abc import Mapping
from dataclasses import dataclass
from http.client import HTTPException
from pathlib import Path
from typing import Protocol

from arxiv_int.readiness.http_transport import fetch_json


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Captured result from one bounded command."""

    returncode: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False


@dataclass(frozen=True, slots=True)
class HttpResult:
    """Captured result from one bounded local HTTP request."""

    status: int | None
    payload: object | None = None
    error: str | None = None


class Probe(Protocol):
    """Injectable boundary for deterministic readiness tests."""

    def which(self, executable: str) -> str | None:
        """Return an executable path when one is available."""
        ...

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        environment: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CommandResult:
        """Run one command without a shell."""
        ...

    def get_json(self, url: str, *, timeout: float) -> HttpResult:
        """Fetch JSON from a local endpoint."""
        ...

    def memory_bytes(self) -> int | None:
        """Return total host memory when measurable."""
        ...


class LocalProbe:
    """Production implementation of bounded and shell-free probes."""

    def which(self, executable: str) -> str | None:
        return shutil.which(executable)

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        environment: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CommandResult:
        try:
            completed = subprocess.run(
                command,
                cwd=cwd,
                env=None if environment is None else dict(environment),
                capture_output=True,
                text=True,
                check=False,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as error:
            return CommandResult(
                124,
                stdout=_text(error.stdout),
                stderr=_text(error.stderr),
                timed_out=True,
            )
        except OSError as error:
            return CommandResult(127, stderr=str(error))
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)

    def get_json(self, url: str, *, timeout: float) -> HttpResult:
        try:
            status, payload = fetch_json(url, timeout=timeout)
            return HttpResult(status, payload, None if status == 200 else f"HTTP {status}")
        except (HTTPException, OSError, ValueError, RecursionError) as error:
            return HttpResult(None, error=error.__class__.__name__)

    def memory_bytes(self) -> int | None:
        page_size = os.sysconf("SC_PAGE_SIZE")
        pages = os.sysconf("SC_PHYS_PAGES")
        return page_size * pages if page_size > 0 and pages > 0 else None


def _text(value: str | bytes | None) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value or ""

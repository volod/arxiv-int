"""Bounded subprocess execution for local extraction tools."""

import os
import re
import signal
import subprocess
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from arxiv_int.extraction.model import ExtractionError

_ABSOLUTE_PATH = re.compile(r"(?<![\w:])/[^\s:;,]+")


@dataclass(frozen=True, slots=True)
class CommandResult:
    """Captured bounded command output."""

    stdout: bytes
    stderr: bytes


def run_command(
    command: tuple[str, ...],
    *,
    timeout_seconds: int,
    output_bytes: int,
    scratch: Path,
    environment: Mapping[str, str] | None = None,
) -> CommandResult:
    """Run without a shell, kill the process group on timeout, and bound captured bytes."""
    scratch.mkdir(parents=True, exist_ok=True)
    tool = Path(command[0]).name
    with (
        tempfile.TemporaryFile(dir=scratch) as stdout,
        tempfile.TemporaryFile(dir=scratch) as stderr,
    ):
        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.DEVNULL,
                stdout=stdout,
                stderr=stderr,
                start_new_session=True,
                env=None if environment is None else {**os.environ, **environment},
            )
        except FileNotFoundError as error:
            raise ExtractionError("tool-unavailable", f"missing extraction tool: {tool}") from error
        try:
            return_code = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired as error:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except PermissionError:
                process.kill()
            process.wait()
            raise ExtractionError(
                "tool-timeout", f"{tool} exceeded {timeout_seconds} seconds"
            ) from error
        captured_stdout = _read_bounded(stdout, output_bytes, tool)
        captured_stderr = _read_bounded(stderr, output_bytes, tool)
    if return_code:
        detail = _failure_detail(captured_stderr, command[0], scratch)
        raise ExtractionError("tool-failed", f"{tool} exited {return_code}: {detail}")
    return CommandResult(captured_stdout, captured_stderr)


def tool_version(
    command: tuple[str, ...], *, timeout_seconds: int, output_bytes: int, scratch: Path
) -> str:
    """Return a bounded first version line."""
    result = run_command(
        command,
        timeout_seconds=timeout_seconds,
        output_bytes=output_bytes,
        scratch=scratch,
    )
    text = (result.stdout or result.stderr).decode("utf-8", errors="replace")
    return text.splitlines()[0].strip()[:200] or "unknown"


def _read_bounded(handle: BinaryIO, limit: int, tool: str) -> bytes:
    handle.seek(0)
    payload = handle.read(limit + 1)
    if len(payload) > limit:
        raise ExtractionError("tool-output-limit", f"{tool} output exceeded {limit} bytes")
    return payload


def _failure_detail(stderr: bytes, executable: str, scratch: Path) -> str:
    """Return one actionable stderr line without host-specific paths."""
    del executable, scratch
    lines = stderr.decode("utf-8", errors="replace").splitlines()
    detail = next((line.strip() for line in reversed(lines) if line.strip()), "no stderr")
    return _ABSOLUTE_PATH.sub("<path>", detail)[:1000]

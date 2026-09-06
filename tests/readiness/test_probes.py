"""Network-free tests for the production probe boundary."""

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from urllib.error import URLError

import pytest

from arxiv_int.readiness.probes import LocalProbe


class FixtureResponse:
    """Minimal context-managed HTTP response."""

    def __init__(self, payload: object) -> None:
        self.status = 200
        self._body = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> "FixtureResponse":
        return self

    def __exit__(self, *args: object) -> None:
        del args

    def read(self) -> bytes:
        return self._body


def test_local_command_probe_captures_success_os_error_and_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    probe = LocalProbe()
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="ok\n", stderr=""),
    )
    assert probe.run(("fixture",), cwd=tmp_path, timeout=1).stdout == "ok\n"

    def os_error(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise OSError("missing")

    monkeypatch.setattr(subprocess, "run", os_error)
    assert probe.run(("fixture",), cwd=tmp_path, timeout=1).returncode == 127

    def timeout(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise subprocess.TimeoutExpired(("fixture",), 1, output=b"partial")

    monkeypatch.setattr(subprocess, "run", timeout)
    result = probe.run(("fixture",), cwd=tmp_path, timeout=1)
    assert result.timed_out is True
    assert result.stdout == "partial"


def test_local_http_probe_decodes_json_and_sanitizes_connection_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    probe = LocalProbe()
    monkeypatch.setattr(
        "arxiv_int.readiness.probes.urlopen",
        lambda *args, **kwargs: FixtureResponse({"models": []}),
    )
    result = probe.get_json("http://127.0.0.1:11434/api/tags", timeout=1)
    assert result.status == 200
    assert result.payload == {"models": []}

    def unavailable(*args: object, **kwargs: object) -> None:
        del args, kwargs
        raise URLError(ConnectionRefusedError("private endpoint detail"))

    monkeypatch.setattr("arxiv_int.readiness.probes.urlopen", unavailable)
    result = probe.get_json("http://127.0.0.1:11434/api/tags", timeout=1)
    assert result.status is None
    assert result.error == "ConnectionRefusedError"
    assert "private endpoint detail" not in result.error


def test_local_memory_probe_uses_host_page_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {"SC_PAGE_SIZE": 4096, "SC_PHYS_PAGES": 100}
    monkeypatch.setattr("arxiv_int.readiness.probes.os.sysconf", values.__getitem__)

    assert LocalProbe().memory_bytes() == 409_600

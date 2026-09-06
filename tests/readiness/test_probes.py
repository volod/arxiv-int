"""Network-free tests for the production probe boundary."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from arxiv_int.readiness.probes import LocalProbe


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


def test_local_memory_probe_uses_host_page_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    values = {"SC_PAGE_SIZE": 4096, "SC_PHYS_PAGES": 100}
    monkeypatch.setattr("arxiv_int.readiness.probes.os.sysconf", values.__getitem__)

    assert LocalProbe().memory_bytes() == 409_600

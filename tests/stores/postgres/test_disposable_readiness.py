"""A bootstrap socket is not the final disposable database service."""

from subprocess import CompletedProcess

import pytest

from arxiv_int.stores.postgres_image import probe_steps


def test_bootstrap_ready_socket_is_not_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    reads: list[str] = []
    logs = iter(
        [
            "ParadeDB bootstrap completed\ndatabase system is ready to accept connections",
            "PostgreSQL init process complete; ready for start up.\n"
            "database system is ready to accept connections",
        ]
    )

    def run(args: list[str], **kwargs: object) -> CompletedProcess[str]:
        if args[1] == "logs":
            value = next(logs)
            reads.append(value)
            return CompletedProcess(args, 0, value, "")
        return CompletedProcess(args, 0, "accepting connections", "")

    monkeypatch.setattr(probe_steps.subprocess, "run", run)
    monkeypatch.setattr(probe_steps.time, "sleep", lambda _: None)
    assert probe_steps.wait_ready("fixture", "fixture", "fixture")
    assert len(reads) == 2

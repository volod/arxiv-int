"""Tests for read-only database extension readiness checks."""

from collections.abc import Mapping
from pathlib import Path

import pytest

from arxiv_int.readiness.database import check_database
from arxiv_int.readiness.probes import CommandResult
from arxiv_int.readiness.report import PreflightReport
from arxiv_int.runtime import load_runtime_config


class RecordingProbe:
    """Capture the extension probe command without running Docker."""

    def __init__(self, result: CommandResult) -> None:
        self.result = result
        self.commands: list[tuple[str, ...]] = []
        self.environments: list[Mapping[str, str] | None] = []

    def which(self, executable: str) -> str | None:
        del executable
        return "/usr/bin/docker"

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        environment: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CommandResult:
        del cwd, timeout
        self.environments.append(environment)
        self.commands.append(command)
        return self.result

    def get_json(self, url: str, *, timeout: float) -> object:
        del url, timeout
        raise AssertionError("HTTP is unused by database checks")

    def memory_bytes(self) -> int | None:
        return None


def _config(tmp_path: Path):
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (checkout / ".env").write_text(
        "ARCHIVE_DIR=unused\nRESULTS_DIR=unused\nPGDATA_DIR=unused\n", encoding="utf-8"
    )
    archive = tmp_path / "archive"
    archive.mkdir()
    return load_runtime_config(
        project_root=checkout,
        environment={
            "ARCHIVE_DIR": str(archive),
            "RESULTS_DIR": str(tmp_path / "results"),
            "PGDATA_DIR": str(tmp_path / "pgdata"),
            "POSTGRES_PASSWORD": "fixture-secret-never-rendered",
            "POSTGRES_USER": "fixture_role",
            "POSTGRES_DB": "fixture_db",
        },
    )


def test_extension_probe_uses_configured_role_not_container_os_uid(tmp_path: Path) -> None:
    probe = RecordingProbe(CommandResult(0, "pg_search=0.25.6/0.25.6\nvector=0.8.4/0.8.4\n"))
    report = PreflightReport("database")

    check_database(
        report,
        _config(tmp_path),
        ("core", "ui", "observability"),
        probe,
        5.0,
        database_healthy=True,
    )

    assert len(probe.commands) == 1
    command = probe.commands[0]
    assert command[command.index("-U") + 1] == "fixture_role"
    assert command[command.index("-d") + 1] == "fixture_db"
    assert "fixture-secret-never-rendered" not in " ".join(command)
    assert "PGPASSWORD" in command
    assert probe.environments[0]["PGPASSWORD"] == "fixture-secret-never-rendered"
    assert report.status == "ready"
    assert any(item.name == "database.extensions" for item in report.findings)


def test_extension_probe_failure_omits_password_from_detail(tmp_path: Path) -> None:
    probe = RecordingProbe(
        CommandResult(2, stderr="psql: error: local user with ID 1000 does not exist")
    )
    report = PreflightReport("database")

    check_database(
        report,
        _config(tmp_path),
        ("core",),
        probe,
        5.0,
        database_healthy=True,
    )

    finding = next(item for item in report.findings if item.name == "database.extensions")
    assert finding.status == "degraded"
    assert finding.detail == "extension version query failed"
    assert "fixture-secret-never-rendered" not in finding.detail


@pytest.mark.parametrize(
    "output", ["pg_search=1/-\nvector=1/-", "pg_search=1/1", "pg_search=1/\nvector=1/1"]
)
def test_uninstalled_or_absent_extensions_block(tmp_path: Path, output: str) -> None:
    report = PreflightReport("database")
    check_database(
        report,
        _config(tmp_path),
        ("core",),
        RecordingProbe(CommandResult(0, output)),
        1,
        database_healthy=True,
    )
    assert report.status == "blocked"


@pytest.mark.parametrize("code", [0, 2])
def test_database_output_never_echoes_credentials(tmp_path: Path, code: int, caplog) -> None:
    secret = "fixture-secret-never-rendered"
    report = PreflightReport("database")
    probe = RecordingProbe(
        CommandResult(code, f"pg_search=1/{secret}\nvector=1/1", f"error {secret}")
    )
    check_database(report, _config(tmp_path), ("core",), probe, 1, database_healthy=True)
    assert secret not in "\n".join(report.console_lines())
    assert secret not in caplog.text


@pytest.mark.parametrize("profiles,expected", [(("core",), "ready"), (("graph",), "blocked")])
def test_age_installation_only_required_for_graph(
    tmp_path: Path, profiles: tuple[str, ...], expected: str
) -> None:
    report = PreflightReport("database")
    probe = RecordingProbe(CommandResult(0, "age=1/-\npg_search=1/1\nvector=1/1"))
    check_database(report, _config(tmp_path), profiles, probe, 1, database_healthy=True)
    assert report.status == expected

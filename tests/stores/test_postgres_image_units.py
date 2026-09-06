"""Unit coverage for PostgreSQL image helpers that do not start containers."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from arxiv_int.stores.postgres_image.build import build_postgres_image
from arxiv_int.stores.postgres_image.commands import run_build_command, run_probe_command
from arxiv_int.stores.postgres_image.pins import load_image_pins
from arxiv_int.stores.postgres_image.probe_model import ProbeReport
from arxiv_int.stores.postgres_image.probe_steps import check_licenses
from arxiv_int.stores.postgres_image.probes import (
    disposable_database_run_args,
    run_extension_probes,
)


def test_probe_report_summary_and_core_gate() -> None:
    report = ProbeReport(image_ref="arxiv-int/postgres:test")
    report.add("licenses", True, "ok")
    report.add("versions", True, "ok")
    report.add("sql", True, "ok")
    report.add("bm25_vector", True, "ok")
    report.add("transaction", True, "ok")
    report.add("restart", True, "ok")
    report.add("dump_restore", True, "ok")
    report.add("cypher", False, "AGE missing")
    assert report.all_core_passed is True
    assert report.summary["cypher"].startswith("fail:")
    assert report.summary["licenses"] == "pass"


def test_check_licenses_records_missing_names() -> None:
    report = ProbeReport()
    check_licenses("no licenses here", report)
    assert report.results[0].ok is False
    check_licenses(
        "AGPL-3.0 Apache License PostgreSQL Apache AGE ParadeDB",
        report,
    )
    assert report.results[1].ok is True


def test_disposable_run_args_include_host_user(tmp_path: Path) -> None:
    args = disposable_database_run_args(
        container="c1",
        image_ref="arxiv-int/postgres:test",
        pgdata_dir=tmp_path,
        password="secret",
        db_user="arxiv_int",
        database="arxiv_int",
    )
    assert args[0] == "docker"
    assert "--user" in args
    assert f"{tmp_path}:/var/lib/postgresql/data" in args


def test_extension_probes_without_docker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr("arxiv_int.stores.postgres_image.probes.shutil.which", lambda _: None)
    report = run_extension_probes(tmp_path, tmp_path / "pgdata")
    assert report.results[0].name == "docker"
    assert report.results[0].ok is False


def test_build_image_invokes_docker(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    pins = load_image_pins(root)
    seen: list[list[str]] = []

    def fake_run(command: list[str], check: bool, cwd: Path) -> SimpleNamespace:
        del check
        seen.append(command)
        assert cwd == root
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr("arxiv_int.stores.postgres_image.build.subprocess.run", fake_run)
    resolved = build_postgres_image(root, pins=pins, no_cache=True)
    assert resolved.local_image_ref == pins.local_image_ref
    assert "--no-cache" in seen[0]


def test_build_image_failure_is_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = Path(__file__).resolve().parents[2]
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.build.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1),
    )
    with pytest.raises(RuntimeError, match="docker build failed"):
        build_postgres_image(root)


def test_probe_command_writes_gate_and_exit_codes(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = Path(__file__).resolve().parents[2]
    passing = ProbeReport(image_ref="arxiv-int/postgres:test", age_compatible=True)
    passing.add("start", True, "ok")
    for name in (
        "licenses",
        "versions",
        "sql",
        "bm25_vector",
        "transaction",
        "restart",
        "dump_restore",
    ):
        passing.add(name, True, "ok")
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.commands.run_extension_probes",
        lambda *args, **kwargs: passing,
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.commands.write_age_compatibility",
        lambda *args, **kwargs: None,
    )
    assert run_probe_command(root, tmp_path, write_gate=True) == 0

    failing = ProbeReport(image_ref="arxiv-int/postgres:test", age_compatible=False)
    failing.add("start", True, "ok")
    failing.add("licenses", False, "missing")
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.commands.run_extension_probes",
        lambda *args, **kwargs: failing,
    )
    assert run_probe_command(root, tmp_path, write_gate=False) == 1

    age_fail = ProbeReport(image_ref="arxiv-int/postgres:test", age_compatible=False)
    age_fail.add("start", True, "ok")
    for name in (
        "licenses",
        "versions",
        "sql",
        "bm25_vector",
        "transaction",
        "restart",
        "dump_restore",
    ):
        age_fail.add(name, True, "ok")
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.commands.run_extension_probes",
        lambda *args, **kwargs: age_fail,
    )
    assert run_probe_command(root, tmp_path, write_gate=False) == 2
    assert run_probe_command(root, tmp_path, write_gate=True) == 0


def test_build_command_prints_tag(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    root = Path(__file__).resolve().parents[2]
    pins = load_image_pins(root)
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.commands.build_postgres_image",
        lambda project_root, no_cache: pins,
    )
    assert run_build_command(root, no_cache=False) == 0
    assert pins.local_image_ref in capsys.readouterr().out


def test_wait_ready_times_out(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("arxiv_int.stores.postgres_image.probe_steps.time.sleep", lambda _: None)
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.probe_steps.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr=""),
    )
    from arxiv_int.stores.postgres_image.probe_steps import wait_ready

    assert wait_ready("c", "u", "d") is False


def test_named_and_dump_probe_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    from arxiv_int.stores.postgres_image.probe_steps import (
        probe_dump_restore,
        probe_named,
        probe_versions,
    )

    failed = SimpleNamespace(returncode=1, stdout="", stderr="nope")
    monkeypatch.setattr("arxiv_int.stores.postgres_image.probe_steps.psql", lambda *a, **k: failed)
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.probe_steps.subprocess.run",
        lambda *a, **k: failed,
    )
    report = ProbeReport()
    assert probe_named("c", "u", "d", "p", "cypher", "SELECT 1", report) is False
    probe_dump_restore("c", "u", "d", "p", report)
    pins = load_image_pins(Path(__file__).resolve().parents[2])
    probe_versions("c", "u", "d", "p", pins, report)
    names = {item.name for item in report.results}
    assert "cypher" in names
    assert "dump_restore" in names
    assert "versions" in names


def test_probe_versions_accepts_expected_inventory(monkeypatch: pytest.MonkeyPatch) -> None:
    from arxiv_int.stores.postgres_image.probe_steps import probe_versions

    pins = load_image_pins(Path(__file__).resolve().parents[2])
    stdout = "\n".join(
        [
            "pg_search,pg_cron,pg_stat_statements,age",
            f"vector={pins.vector_version}",
            f"pg_search={pins.pg_search_version}",
            f"age={pins.age_version}",
        ]
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.probe_steps.psql",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=stdout, stderr=""),
    )
    report = ProbeReport()
    probe_versions("c", "u", "d", "p", pins, report)
    assert {item.name: item.ok for item in report.results}["versions"] is True


def test_probe_restart_records_start_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    from arxiv_int.stores.postgres_image.probe_steps import probe_restart

    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.probe_steps.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="restart failed"),
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.probe_steps.wait_ready",
        lambda *args, **kwargs: False,
    )
    report = ProbeReport()
    probe_restart("c", ["docker", "run", "img"], "u", "d", "p", report)
    assert any(item.name == "restart" and not item.ok for item in report.results)

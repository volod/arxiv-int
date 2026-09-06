"""Branch coverage for schema binding, CLI, dotenv, and coordinator edges."""

import json
from argparse import Namespace
from pathlib import Path

import pytest

from arxiv_int.contracts.migrations.runner import STATUS_FAILED, RunnerOutcome
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.project_root import ProjectRootError
from arxiv_int.runtime.setup.adapters import (
    default_build_image,
    default_command_run,
    production_adapters,
)
from arxiv_int.runtime.setup.commands import resolve_cli_profiles, run_setup_command
from arxiv_int.runtime.setup.config_phase import run_config_phase
from arxiv_int.runtime.setup.coordinator import run_setup
from arxiv_int.runtime.setup.env_file import missing_required_edits, sync_dotenv_file
from arxiv_int.runtime.setup.host import docker_compose_available
from arxiv_int.runtime.setup.lock import concurrent_block
from arxiv_int.runtime.setup.model import PhaseResult
from arxiv_int.runtime.setup.report import (
    SetupReport,
    aggregate_status,
    console_lines,
    persist_setup_report,
)
from arxiv_int.runtime.setup.requirements import resolve_requirements
from arxiv_int.runtime.setup.schema import bound_service_url, run_schema_phase
from arxiv_int.runtime.setup.settings import load_setup_settings
from arxiv_int.runtime.setup.state import load_verified, matches, store_verified
from arxiv_int.stores.postgres.apply import SchemaApplyReport
from tests.runtime.setup.conftest import checkout, make_adapters, operator_env


def _config(tmp_path: Path):
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    return load_runtime_config(project_root=root, environment=environment), root, environment


def test_schema_accepts_localhost_alias(tmp_path: Path) -> None:
    config, _root, _environment = _config(tmp_path)
    matching = bound_service_url(
        config, "postgresql+psycopg://arxiv_int:fixture-secret@localhost:5432/arxiv_int"
    )
    assert "127.0.0.1" in matching


def test_schema_refuses_non_loopback_service(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, _root, _environment = _config(tmp_path)
    remote = "postgresql+psycopg://arxiv_int:x@example.com:5432/arxiv_int"
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.service_database_url", lambda _config: remote
    )
    with pytest.raises(ValueError, match="loopback"):
        bound_service_url(config, remote)


def test_schema_inspect_failure_and_unversioned(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config, _root, _environment = _config(tmp_path)
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.inspect_and_compare",
        lambda *_a, **_k: (_ for _ in ()).throw(RuntimeError("down")),
    )
    assert run_schema_phase(config, override=None, run_id="t").status == "blocked"
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.inspect_and_compare",
        lambda *_a, **_k: ([], {"schemas": ["ctl"]}, None),
    )
    unversioned = run_schema_phase(config, override=None, run_id="t")
    assert "unversioned" in unversioned.detail


def test_schema_at_head_and_apply_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config, _root, _environment = _config(tmp_path)
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.inspect_and_compare",
        lambda *_a, **_k: ([], {"schemas": ["ctl"]}, "0002"),
    )
    at_head = run_schema_phase(config, override=None, run_id="t", verified={})
    assert at_head.status == "ready"
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.inspect_and_compare",
        lambda *_a, **_k: ([], {"schemas": []}, None),
    )
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.apply_revisions",
        lambda *_a, **_k: SchemaApplyReport(
            RunnerOutcome(STATUS_FAILED, "refused"), ("blocked",), Path("e"), None, {}
        ),
    )
    assert run_schema_phase(config, override=None, run_id="t").status == "blocked"


def test_schema_phase_reports_conflicting_override(tmp_path: Path) -> None:
    config, _root, _environment = _config(tmp_path)
    result = run_schema_phase(
        config,
        override="postgresql+psycopg://x:y@127.0.0.1:9/scratch",
        run_id="t",
    )
    assert result.status == "blocked"


def test_sync_dotenv_errors_and_export_append(tmp_path: Path) -> None:
    root = checkout(tmp_path, example=False, dotenv=None)
    with pytest.raises(Exception, match="missing"):
        sync_dotenv_file(root)
    (root / ".env.example").write_text("DATA_DIR=.data\n", encoding="utf-8")
    (root / ".env").mkdir()
    with pytest.raises(Exception, match="regular file"):
        sync_dotenv_file(root)
    (root / ".env").rmdir()
    (root / ".env").write_text("export KEEP=1\n", encoding="utf-8")
    (root / ".env.example").write_text("export KEEP=1\nNEW_SETUP_VAR=1\n", encoding="utf-8")
    assert "added" in sync_dotenv_file(root)


def test_missing_edits_and_password(tmp_path: Path) -> None:
    root = checkout(tmp_path, dotenv="DATA_DIR=.data\n")
    assert missing_required_edits(root, {"ARCHIVE_DIR": "/missing"})
    pw_dir = tmp_path / "pw"
    pw_dir.mkdir()
    password_root = checkout(pw_dir)
    environment = operator_env(pw_dir, password_root, POSTGRES_PASSWORD="")
    environment["POSTGRES_PASSWORD"] = ""
    assert "POSTGRES_PASSWORD" in missing_required_edits(password_root, environment)


def test_verified_state_corrupt_and_empty_match(tmp_path: Path) -> None:
    data_dir = tmp_path / "state"
    assert load_verified(data_dir) == {}
    store_verified(data_dir, {"env": "abc"})
    (data_dir / "setup" / "verified.json").write_text("{", encoding="utf-8")
    assert load_verified(data_dir) == {}
    (data_dir / "setup" / "verified.json").write_text(json.dumps(["nope"]), encoding="utf-8")
    assert load_verified(data_dir) == {}
    assert not matches({}, "env", "")


def test_unknown_profile_and_vllm_requirement_union(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    operator_env(tmp_path, root)
    settings = load_setup_settings(
        project_root=root, environment={"PIPELINE_PROFILE": "not-a-profile"}
    )
    with pytest.raises(ValueError, match="unknown PIPELINE_PROFILE"):
        resolve_requirements(settings)
    vllm = load_setup_settings(project_root=root, environment={"INFERENCE_BACKEND": "vllm"})
    required = resolve_requirements(vllm, {"INFERENCE_BACKEND": "vllm"})
    assert "vllm" in required.service_profiles


def test_load_settings_rejects_malformed_dotenv(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    (root / ".env").write_text("this is not an assignment\n", encoding="utf-8")
    with pytest.raises(Exception, match="NAME=value"):
        load_setup_settings(project_root=root)


def test_setup_command_root_error_and_profile_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.commands.find_project_root",
        lambda *_a, **_k: (_ for _ in ()).throw(ProjectRootError("no root")),
    )
    assert run_setup_command(Namespace(phase=None, project_root=None)) == 1
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.settings.load_setup_settings",
        lambda **_k: (_ for _ in ()).throw(ValueError("bad")),
    )
    assert resolve_cli_profiles(None, tmp_path) == "pipeline"


def test_adapters_host_lock_and_build_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert docker_compose_available(lambda _name: "/usr/bin/docker")
    assert concurrent_block("held").status == "blocked"
    assert production_adapters().probe is not None
    assert default_command_run(("true",), cwd=tmp_path).returncode == 0
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.adapters.build_postgres_image",
        lambda _root: (_ for _ in ()).throw(RuntimeError("no docker")),
    )
    assert default_build_image(tmp_path) == 1


def test_atomic_schema_relative_data_dir(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    environment["DATA_DIR"] = "relative-data"
    report = run_setup(
        project_root=root,
        phase="schema",
        environment=environment,
        adapters=make_adapters(root),
    )
    assert report.phases[0].name == "schema"


def test_unknown_phase_and_report_rendering(tmp_path: Path) -> None:
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    with pytest.raises(ValueError, match="unknown setup phase"):
        run_setup(
            project_root=root,
            phase="not-a-phase",
            environment=environment,
            adapters=make_adapters(root),
        )
    report = SetupReport(
        "a",
        "ready",
        (PhaseResult("config", "ready", "ok", action="make setup"),),
        "ready",
        "unavailable",
        "setup complete",
    )
    assert persist_setup_report(report, None) is None
    assert any("next:" in line for line in console_lines(report))
    assert aggregate_status((PhaseResult("config", "degraded", "slow"),)) == "degraded"


def test_persist_setup_report_and_config_without_example(tmp_path: Path) -> None:
    config, _root, _environment = _config(tmp_path)
    report = SetupReport("a", "ready", (), "ready", "unavailable", "setup complete")
    written = persist_setup_report(report, config)
    assert written is not None
    other = tmp_path / "other"
    other.mkdir()
    blocked, loaded = run_config_phase(
        checkout(other, example=False, dotenv=None),
        which=lambda _name: "/bin/true",
        environment={},
    )
    assert loaded is None
    assert blocked.status == "blocked"

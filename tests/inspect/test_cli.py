"""CLI, Make, and run-artifact inspection."""

from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main
from arxiv_int.pipeline.dag.actions import fixture_plan
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.run.fixtures import (
    FIXTURE_OPTIONAL,
    FIXTURE_PROFILE_STAGES,
    fixture_registry,
)
from arxiv_int.runtime.project_root import find_project_root
from tests.pipeline.conftest import make_context


def test_cli_help_lists_inspect_and_run_artifacts() -> None:
    parser = build_parser()
    text = parser.format_help()
    assert "inspect" in text
    inspect_help = _subcommand_help(parser, ["inspect", "--help"])
    assert "latest" in inspect_help
    assert "--limit" in inspect_help
    parsed = parser.parse_args(["inspect", "run-abc", "--limit", "3", "--json"])
    assert parsed.target == "run-abc"
    assert parsed.limit == 3
    artifacts = parser.parse_args(["run", "artifacts", "run-abc"])
    assert artifacts.run_command == "artifacts"
    assert artifacts.run_id == "run-abc"


def test_inspect_cli_and_run_artifacts_alias(
    tmp_path: Path, caplog, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    import logging

    _clear_operator_roots(monkeypatch)
    monkeypatch.setattr(
        "arxiv_int.inspect.commands.load_runtime_config",
        _refuse_runtime_config,
    )
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    Orchestrator(registry, context.runs_dir).execute_plan(
        context,
        fixture_plan(
            registry,
            profile_stages=FIXTURE_PROFILE_STAGES,
            optional_stages=FIXTURE_OPTIONAL,
        ),
    )
    caplog.set_level(logging.INFO)
    code = main(
        [
            "inspect",
            context.run_id,
            "--runs-dir",
            str(context.runs_dir),
            "--results-dir",
            str(context.results_dir),
            "--project-root",
            str(find_project_root()),
        ]
    )
    assert code == 0
    assert f"run_id={context.run_id}" in caplog.text
    assert "stage=alpha" in caplog.text
    caplog.clear()
    alias = main(
        [
            "run",
            "artifacts",
            context.run_id,
            "--runs-dir",
            str(context.runs_dir),
            "--results-dir",
            str(context.results_dir),
            "--project-root",
            str(find_project_root()),
            "--json",
        ]
    )
    assert alias == 0
    captured = capsys.readouterr()
    assert "arxiv-int.inspect.v1" in captured.out
    assert context.run_id in captured.out


def test_inspect_cli_refuses_local(tmp_path: Path, caplog, monkeypatch: pytest.MonkeyPatch) -> None:
    import logging

    _clear_operator_roots(monkeypatch)
    monkeypatch.setattr(
        "arxiv_int.inspect.commands.load_runtime_config",
        _refuse_runtime_config,
    )
    caplog.set_level(logging.ERROR)
    code = main(
        [
            "inspect",
            "local",
            "--runs-dir",
            str(tmp_path / "runs"),
            "--project-root",
            str(find_project_root()),
        ]
    )
    assert code == 1
    assert "developer alias" in caplog.text


def _clear_operator_roots(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("ARCHIVE_DIR", "RESULTS_DIR", "PGDATA_DIR", "RUNS_DIR"):
        monkeypatch.delenv(name, raising=False)


def _refuse_runtime_config(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("explicit run paths must not load operator runtime config")


def _subcommand_help(parser: object, argv: list[str]) -> str:
    from io import StringIO
    from unittest.mock import patch

    with patch("sys.stdout", new_callable=StringIO) as stdout:
        try:
            parser.parse_args(argv)  # type: ignore[attr-defined]
        except SystemExit:
            return stdout.getvalue()
    return stdout.getvalue()

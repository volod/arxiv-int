"""CLI, Make, and evaluate-stage inspection."""

from pathlib import Path

from arxiv_int.cli import build_parser, main
from arxiv_int.evaluation.stage import EvaluateStage
from arxiv_int.inspect.model import KIND_RUN
from arxiv_int.inspect.summarize import inspect_run
from arxiv_int.pipeline.actions import fixture_plan
from arxiv_int.pipeline.fixtures import FIXTURE_OPTIONAL, FIXTURE_PROFILE_STAGES, fixture_registry
from arxiv_int.pipeline.orchestrate import Orchestrator
from arxiv_int.pipeline.registry import ResourceEstimate, StageRegistry, StageSpec
from arxiv_int.runtime.project_root import find_project_root
from tests.pipeline.orchestration.conftest import make_context


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


def test_inspect_cli_and_run_artifacts_alias(tmp_path: Path, caplog, capsys) -> None:
    import logging

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


def test_inspect_cli_refuses_local(tmp_path: Path) -> None:
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


def test_inspect_evaluate_stage_artifacts(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    from dataclasses import replace

    context = replace(make_context(tmp_path), project_root=find_project_root())
    from arxiv_int.pipeline.persist import save_context

    save_context(context)
    estimate = ResourceEstimate()
    registry = StageRegistry(
        (StageSpec("evaluate", "1", (), (), (), estimate, (), (), EvaluateStage()),)
    )
    plan = fixture_plan(registry, profile_stages=("evaluate",))
    result = Orchestrator(registry, context.runs_dir).execute_plan(context, plan)
    assert not result.halted
    summary = inspect_run(
        context.runs_dir,
        context.run_id,
        results_dir=context.results_dir,
        project_root=find_project_root(),
    )
    assert summary.kind == KIND_RUN
    evaluate = next(item for item in summary.stages if item.stage == "evaluate")
    assert evaluate.outcome == "produced"
    assert evaluate.tree_valid
    assert evaluate.files


def _subcommand_help(parser: object, argv: list[str]) -> str:
    from io import StringIO
    from unittest.mock import patch

    with patch("sys.stdout", new_callable=StringIO) as stdout:
        try:
            parser.parse_args(argv)  # type: ignore[attr-defined]
        except SystemExit:
            return stdout.getvalue()
    return stdout.getvalue()

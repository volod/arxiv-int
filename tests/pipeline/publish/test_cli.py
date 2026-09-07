"""CLI and Make wrappers for run finalize."""

import ast
import subprocess
from pathlib import Path

from arxiv_int.cli import build_parser, main
from arxiv_int.pipeline.actions import fixture_plan
from arxiv_int.pipeline.fixtures import FIXTURE_OPTIONAL, FIXTURE_PROFILE_STAGES, fixture_registry
from arxiv_int.pipeline.orchestrate import Orchestrator
from tests.pipeline.orchestration.conftest import make_context

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PUBLISH_ROOT = PROJECT_ROOT / "src" / "arxiv_int" / "pipeline" / "publish"
BLOCKED = frozenset({"sqlalchemy", "alembic", "psycopg", "pandera", "dbt"})


def test_cli_help_lists_finalize() -> None:
    parser = build_parser()
    text = _subcommand_help(parser, ["run", "finalize", "--help"])
    assert "knowledge-base" in text or "finalize" in text
    parsed = parser.parse_args(["run", "finalize", "run-abc"])
    assert parsed.run_command == "finalize"
    assert parsed.run_id == "run-abc"


def test_make_help_lists_run_finalize() -> None:
    help_text = subprocess.run(
        ["make", "--no-print-directory", "help"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "run-finalize" in help_text
    dry = subprocess.run(
        ["make", "--no-print-directory", "--dry-run", "run-finalize", "RUN_ID=run-abc"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "run finalize" in dry
    assert "arxiv_int_require_created_run_id" in dry
    assert "arxiv_int_load_env" in dry


def test_run_finalize_cli_seals_a_fixture_generation(tmp_path: Path) -> None:
    registry, _runners = fixture_registry()
    context = make_context(tmp_path)
    plan = fixture_plan(
        registry,
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
    )
    Orchestrator(registry, context.runs_dir).execute_plan(context, plan)
    code = main(
        [
            "run",
            "finalize",
            context.run_id,
            "--runs-dir",
            str(context.runs_dir),
            "--project-root",
            str(context.project_root),
        ]
    )
    assert code == 0
    assert (context.runs_dir / context.run_id / "knowledge-base.json").is_file()
    assert (context.runs_dir / "active-generation.json").is_file()


def test_publish_modules_do_not_import_heavy_stacks() -> None:
    for path in PUBLISH_ROOT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                names.add(node.module.split(".")[0])
        assert names.isdisjoint(BLOCKED), path.name


def _subcommand_help(parser: object, argv: list[str]) -> str:
    from io import StringIO
    from unittest.mock import patch

    with patch("sys.stdout", new_callable=StringIO) as stdout:
        try:
            parser.parse_args(argv)  # type: ignore[attr-defined]
        except SystemExit:
            return stdout.getvalue()
    return stdout.getvalue()

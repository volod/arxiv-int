"""CLI, Make, and optional-import gates for the forecast command."""

import ast
import os
import subprocess
from pathlib import Path

from arxiv_int.cli import build_parser, main
from arxiv_int.runtime.filesystem import FilesystemEvidence

PROJECT_ROOT = Path(__file__).resolve().parents[3]
FORECAST_ROOT = PROJECT_ROOT / "src" / "arxiv_int" / "pipeline" / "forecast"
BLOCKED = frozenset({"sqlalchemy", "alembic", "psycopg", "pandera", "dbt"})
_RUNTIME_ENV = (
    "ARCHIVE_DIR",
    "RESULTS_DIR",
    "PGDATA_DIR",
    "RUNS_DIR",
    "SERVICE_STATE_DIR",
    "MODEL_CACHE_DIR",
    "TMP_DIR",
    "PG_WAL_DIR",
)


def _clear_runtime_env(monkeypatch: object) -> None:
    for name in _RUNTIME_ENV:
        monkeypatch.delenv(name, raising=False)
    for name in tuple(os.environ):
        if name.startswith(("ARCHIVE_SILO_", "PG_TABLESPACE_")):
            monkeypatch.delenv(name, raising=False)


PROJECT_ROOT = Path(__file__).resolve().parents[3]
FORECAST_ROOT = PROJECT_ROOT / "src" / "arxiv_int" / "pipeline" / "forecast"
BLOCKED = frozenset({"sqlalchemy", "alembic", "psycopg", "pandera", "dbt"})


def _checkout(tmp_path: Path) -> Path:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "doc.txt").write_text("x", encoding="utf-8")
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (checkout / ".env").write_text(
        f"ARCHIVE_DIR={archive}\nRESULTS_DIR={tmp_path / 'results'}\n"
        f"PGDATA_DIR={tmp_path / 'pgdata'}\n",
        encoding="utf-8",
    )
    (tmp_path / "pgdata").mkdir()
    return checkout


def _plentiful(path: Path) -> FilesystemEvidence:
    return FilesystemEvidence(path, "ext4", "8:1", False, 10**18, True, False)


def test_cli_help_lists_forecast() -> None:
    parser = build_parser()
    text = parser.format_help()
    forecast = _subcommand_help(parser, ["pipeline", "forecast", "--help"])
    assert "pipeline" in text
    assert "forecast" in forecast
    parsed = parser.parse_args(["pipeline", "forecast", "--run-id", "run-abc"])
    assert parsed.pipeline_command == "forecast"
    assert parsed.run_id == "run-abc"


def test_standalone_forecast_does_not_create_a_production_generation(
    tmp_path: Path, monkeypatch: object
) -> None:
    _clear_runtime_env(monkeypatch)
    monkeypatch.setattr("arxiv_int.pipeline.forecast.devices.inspect_filesystem", _plentiful)
    checkout = _checkout(tmp_path)
    code = main(
        [
            "pipeline",
            "forecast",
            "--project-root",
            str(checkout),
            "--archive-dir",
            str(tmp_path / "archive"),
            "--results-dir",
            str(tmp_path / "results"),
        ]
    )
    assert code == 0
    runs = tmp_path / "results" / "runs"
    found = list(runs.glob("forecast-*/forecast/decision.json"))
    assert len(found) == 1
    assert not (found[0].parent.parent / "run-context.json").is_file()


def test_run_bound_forecast_writes_under_the_created_run(
    tmp_path: Path, monkeypatch: object
) -> None:
    _clear_runtime_env(monkeypatch)
    monkeypatch.setattr("arxiv_int.pipeline.forecast.devices.inspect_filesystem", _plentiful)
    checkout = _checkout(tmp_path)
    create = main(
        [
            "run",
            "create",
            "--project-root",
            str(checkout),
            "--archive-dir",
            str(tmp_path / "archive"),
            "--results-dir",
            str(tmp_path / "results"),
        ]
    )
    assert create == 0
    run_dir = next((tmp_path / "results" / "runs").glob("run-*"))
    code = main(
        [
            "pipeline",
            "forecast",
            "--project-root",
            str(checkout),
            "--run-id",
            run_dir.name,
        ]
    )
    assert code == 0
    assert (run_dir / "forecast" / "decision.json").is_file()
    assert (run_dir / "run-context.json").is_file()


def test_pipeline_run_forecasts_before_unregistered_stages(
    tmp_path: Path, monkeypatch: object
) -> None:
    _clear_runtime_env(monkeypatch)
    monkeypatch.setattr("arxiv_int.pipeline.forecast.devices.inspect_filesystem", _plentiful)
    checkout = _checkout(tmp_path)
    code = main(
        [
            "pipeline",
            "run",
            "--project-root",
            str(checkout),
            "--archive-dir",
            str(tmp_path / "archive"),
            "--results-dir",
            str(tmp_path / "results"),
        ]
    )
    assert code == 1
    run_dir = next((tmp_path / "results" / "runs").glob("run-*"))
    assert (run_dir / "forecast" / "decision.json").is_file()


def test_make_help_lists_forecast() -> None:
    help_text = subprocess.run(
        ["make", "--no-print-directory", "help"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "forecast" in help_text
    dry = subprocess.run(
        ["make", "--no-print-directory", "--dry-run", "forecast", "RUN_ID=run-abc"],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert "pipeline forecast --run-id" in dry
    assert "arxiv_int_require_created_run_id" in dry


def test_forecast_modules_do_not_import_heavy_stacks() -> None:
    for path in FORECAST_ROOT.glob("*.py"):
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

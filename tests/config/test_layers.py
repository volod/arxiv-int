"""Tests for layered configuration precedence."""

import subprocess
from pathlib import Path

import pytest

from arxiv_int.runtime import ConfigurationError, load_runtime_config, merge_config_layers


def test_layers_apply_cli_environment_dotenv_default_precedence() -> None:
    resolved = merge_config_layers(
        {"ROOT": "default", "MODEL": "default", "EMPTY": "default"},
        {"ROOT": "dotenv", "MODEL": "dotenv", "EMPTY": None},
        {"ROOT": "environment"},
        {"ROOT": "cli", "MODEL": None, "EMPTY": ""},
    )

    assert resolved == {"ROOT": "cli", "MODEL": "dotenv", "EMPTY": ""}


def _checkout(path: Path, dotenv: str = "") -> Path:
    path.mkdir()
    (path / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (path / ".env").write_text(dotenv, encoding="utf-8")
    return path


def test_runtime_config_uses_cli_then_environment_then_dotenv(tmp_path: Path) -> None:
    root = _checkout(
        tmp_path / "checkout",
        "ARCHIVE_DIR=dotenv/archive\nRESULTS_DIR=dotenv/results\nPGDATA_DIR=dotenv/pg\n",
    )
    config = load_runtime_config(
        project_root=root,
        environment={"RESULTS_DIR": "environment/results"},
        cli={"RESULTS_DIR": "cli/results", "PGDATA_DIR": "cli/pg"},
    )

    assert config.archive_silos[0].root == root / "dotenv/archive"
    assert config.results_dir == root / "cli/results"
    assert config.pgdata_dir == root / "cli/pg"
    assert config.runs_dir == config.results_dir / "runs"
    assert config.data_dir == root / ".data"


def test_paths_resolve_from_each_checkout_not_the_current_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = _checkout(
        tmp_path / "first checkout",
        "ARCHIVE_DIR=archive\nRESULTS_DIR=results\nPGDATA_DIR=database\n",
    )
    second = _checkout(
        tmp_path / "second checkout",
        "ARCHIVE_DIR=archive\nRESULTS_DIR=results\nPGDATA_DIR=database\n",
    )
    elsewhere = tmp_path / "unrelated cwd"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    first_config = load_runtime_config(project_root=first, environment={})
    second_config = load_runtime_config(project_root=second, environment={})

    assert first_config.results_dir == first / "results"
    assert second_config.results_dir == second / "results"


def test_named_silos_derived_overrides_and_database_roots(tmp_path: Path) -> None:
    root = _checkout(tmp_path / "checkout")
    config = load_runtime_config(
        project_root=root,
        environment={
            "ARCHIVE_SILO_DRAWINGS_DIR": "source drawings",
            "ARCHIVE_SILO_MANUALS_DIR": "source manuals",
            "RESULTS_DIR": "bulk results",
            "PGDATA_DIR": "fast/pg",
            "RUNS_DIR": "journal disk/runs",
            "TMP_DIR": "fast/tmp",
            "PG_WAL_DIR": "fast/wal",
            "PG_TABLESPACE_COLD_DIR": "fast/cold tables",
        },
    )

    assert [silo.silo_id for silo in config.archive_silos] == ["drawings", "manuals"]
    assert config.archive_silos[0].root == root / "source drawings"
    assert config.runs_dir == root / "journal disk/runs"
    assert config.dev_results_dir == root / "bulk results/dev"
    assert config.pg_tablespaces == (("cold", root / "fast/cold tables"),)


def test_config_references_use_the_merged_value_and_secrets_are_redacted(tmp_path: Path) -> None:
    root = _checkout(tmp_path / "checkout")
    config = load_runtime_config(
        project_root=root,
        environment={
            "ARCHIVE_DIR": "archive",
            "RESULTS_DIR": "environment-results",
            "PGDATA_DIR": "pg",
            "RUNS_DIR": "${RESULTS_DIR}/custom runs",
            "POSTGRES_PASSWORD": "do-not-print-this",
            "DATABASE_URL": "postgresql://secret",
        },
    )

    rendered = "\n".join(config.rendered())
    assert config.runs_dir == root / "environment-results/custom runs"
    assert "do-not-print-this" not in rendered
    assert "postgresql://secret" not in rendered
    assert "POSTGRES_PASSWORD=<redacted>" in rendered
    assert "do-not-print-this" not in repr(config)


def test_missing_roots_and_bad_references_report_variable_names(tmp_path: Path) -> None:
    root = _checkout(tmp_path / "checkout")
    with pytest.raises(ConfigurationError, match=r"ARCHIVE_DIR.*RESULTS_DIR.*PGDATA_DIR"):
        load_runtime_config(project_root=root, environment={})
    with pytest.raises(ConfigurationError, match="RUNS_DIR references missing UNKNOWN_DIR"):
        load_runtime_config(
            project_root=root,
            environment={
                "ARCHIVE_DIR": "archive",
                "RESULTS_DIR": "results",
                "PGDATA_DIR": "pg",
                "RUNS_DIR": "${UNKNOWN_DIR}/runs",
            },
        )


def test_shell_bootstrap_preserves_process_environment_over_dotenv(tmp_path: Path) -> None:
    root = _checkout(tmp_path / "checkout", "RESULTS_DIR=dotenv-results\nDATA_DIR=dotenv-data\n")
    script = Path(__file__).parents[2] / "scripts/shared/common.sh"
    completed = subprocess.run(
        [
            "bash",
            "-c",
            'source "$1"; arxiv_int_load_env; printf "%s\\n%s\\n" "$RESULTS_DIR" "$DATA_DIR"',
            "bash",
            str(script),
        ],
        check=True,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PROJECT_ROOT": str(root), "RESULTS_DIR": "process-results"},
    )

    assert completed.stdout.splitlines() == ["process-results", str(root / "dotenv-data")]

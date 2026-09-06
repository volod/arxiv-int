"""Tests for destructive service-data reset helpers."""

from pathlib import Path

import pytest

from arxiv_int.runtime import (
    ComposeConfigurationError,
    ServiceResetError,
    load_runtime_config,
    reset_service_data,
    run_compose,
    service_data_targets,
)


def _config(tmp_path: Path, **overrides: str):
    checkout = tmp_path / "checkout"
    checkout.mkdir(exist_ok=True)
    (checkout / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (checkout / ".env").write_text(
        "ARCHIVE_DIR=unused\nRESULTS_DIR=unused\nPGDATA_DIR=unused\n", encoding="utf-8"
    )
    archive = tmp_path / "archive"
    archive.mkdir(exist_ok=True)
    values = {
        "ARCHIVE_DIR": str(archive),
        "RESULTS_DIR": str(tmp_path / "results"),
        "PGDATA_DIR": str(tmp_path / "pgdata"),
        "POSTGRES_PASSWORD": "fixture-secret-never-rendered",
        **overrides,
    }
    return load_runtime_config(project_root=checkout, environment=values)


def test_service_data_targets_include_database_state_and_model_cache(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        PG_WAL_DIR=str(tmp_path / "wal"),
        PG_TABLESPACE_COLD_DIR=str(tmp_path / "cold"),
    )
    targets = service_data_targets(config)
    assert config.pgdata_dir.resolve() in targets
    assert config.service_state_dir.resolve() in targets
    assert config.model_cache_dir.resolve() in targets
    assert config.pg_wal_dir is not None and config.pg_wal_dir.resolve() in targets
    assert config.pg_tablespaces[0][1].resolve() in targets
    assert config.results_dir.resolve() not in targets
    assert config.archive_silos[0].root.resolve() not in targets


def test_reset_dry_run_preserves_files_and_apply_clears_them(tmp_path: Path) -> None:
    config = _config(tmp_path)
    for path in (config.pgdata_dir, config.service_state_dir, config.model_cache_dir):
        path.mkdir(parents=True)
        (path / "keep-or-drop.bin").write_bytes(b"data")

    planned = reset_service_data(config, apply=False)
    assert config.pgdata_dir.resolve() in planned
    assert (config.pgdata_dir / "keep-or-drop.bin").is_file()

    reset_service_data(config, apply=True)
    assert config.pgdata_dir.is_dir()
    assert not (config.pgdata_dir / "keep-or-drop.bin").exists()
    assert config.pgdata_dir.stat().st_mode & 0o777 == 0o700
    assert not (config.service_state_dir / "keep-or-drop.bin").exists()
    assert not (config.model_cache_dir / "keep-or-drop.bin").exists()


def test_reset_refuses_results_dir_and_archive_overlap(tmp_path: Path) -> None:
    with pytest.raises(ServiceResetError, match="RESULTS_DIR"):
        reset_service_data(
            _config(tmp_path, SERVICE_STATE_DIR=str(tmp_path / "results")),
            apply=False,
        )
    archive = tmp_path / "archive"
    with pytest.raises(ServiceResetError, match="archive"):
        reset_service_data(
            _config(tmp_path, PGDATA_DIR=str(archive)),
            apply=False,
        )


def test_run_compose_reset_stops_then_optionally_erases(tmp_path: Path) -> None:
    config = _config(tmp_path)
    config.pgdata_dir.mkdir(parents=True)
    marker = config.pgdata_dir / "cluster"
    marker.write_text("alive", encoding="utf-8")
    observed: list[tuple[str, ...]] = []

    assert (
        run_compose(
            config,
            "reset",
            "pipeline",
            apply=False,
            runner=lambda command, _cwd, _environment: observed.append(command) or 0,
        )
        == 0
    )
    assert "down" in observed[0]
    assert marker.is_file()

    assert (
        run_compose(
            config,
            "reset",
            "pipeline",
            apply=True,
            runner=lambda command, _cwd, _environment: observed.append(command) or 0,
        )
        == 0
    )
    assert not marker.exists()


def test_run_compose_reset_surfaces_unsafe_targets(tmp_path: Path) -> None:
    config = _config(tmp_path, SERVICE_STATE_DIR=str(tmp_path / "results"))
    with pytest.raises(ComposeConfigurationError, match="RESULTS_DIR"):
        run_compose(
            config,
            "reset",
            "core",
            apply=False,
            runner=lambda _command, _cwd, _environment: 0,
        )

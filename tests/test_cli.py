import logging
import os
from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main


def test_parser_selects_the_info_command() -> None:
    assert build_parser().parse_args(["info"]).command == "info"


def test_info_command_logs_the_project_identity(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["info"]) == 0
    assert "arxiv-int" in caplog.text
    assert "arxiv_int" in caplog.text


def test_parser_accepts_a_stage_filter_for_features() -> None:
    arguments = build_parser().parse_args(["features", "--stage", "embed"])

    assert arguments.command == "features"
    assert arguments.stage == "embed"


def test_features_command_logs_groups_with_install_commands(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["features"]) == 0
    assert "feature groups" in caplog.text
    assert "uv pip install 'arxiv-int[lake]'" in caplog.text
    assert "reserved for capability: russian-nlp" in caplog.text


def test_features_command_reports_an_unknown_stage(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["features", "--stage", "no-such-stage"]) == 1
    assert "unknown stage" in caplog.text


def test_config_show_applies_cli_roots_redacts_and_creates_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    checkout = tmp_path / "copied checkout"
    checkout.mkdir()
    (checkout / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    archive = tmp_path / "source files"
    archive.mkdir()
    results = tmp_path / "runtime results"
    pgdata = tmp_path / "database"
    for name in tuple(os.environ):
        if name in {"PROOF_ARCHIVE_DIR", "DEV_ARCHIVE_DIR", "PG_WAL_DIR"} or name.startswith(
            ("ARCHIVE_SILO_", "PG_TABLESPACE_")
        ):
            monkeypatch.delenv(name)
    monkeypatch.setenv("POSTGRES_PASSWORD", "must-not-appear")
    caplog.set_level(logging.INFO)

    status = main(
        [
            "config",
            "show",
            "--redact",
            "--project-root",
            str(checkout),
            "--archive-dir",
            str(archive),
            "--results-dir",
            str(results),
            "--pgdata-dir",
            str(pgdata),
            "--runs-dir",
            str(results / "runs"),
            "--dev-results-dir",
            str(results / "dev"),
            "--service-state-dir",
            str(results / "services"),
            "--model-cache-dir",
            str(results / "models"),
            "--tmp-dir",
            str(results / "tmp"),
        ]
    )

    assert status == 0
    assert "must-not-appear" not in caplog.text
    assert "POSTGRES_PASSWORD=<redacted>" in caplog.text
    assert "filesystem=" in caplog.text
    assert (results / "normalized").is_dir()
    assert pgdata.is_dir()

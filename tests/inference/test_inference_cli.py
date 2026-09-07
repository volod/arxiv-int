"""CLI parsing and schema-check command for local inference."""

import logging
from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main
from arxiv_int.inference.schema import generate_schemas


def test_parser_accepts_inference_commands() -> None:
    parser = build_parser()
    assert parser.parse_args(["inference", "health"]).inference_command == "health"
    assert parser.parse_args(["inference", "models"]).inference_command == "models"
    identity = parser.parse_args(["inference", "identity", "--model", "fixture-chat"])
    assert identity.model == "fixture-chat"
    assert parser.parse_args(["inference", "resources"]).inference_command == "resources"
    fit = parser.parse_args(["inference", "fit", "--model", "llama3.2:3b", "--no-allow-cpu"])
    assert fit.inference_command == "fit"
    assert fit.allow_cpu is False
    schedule = parser.parse_args(["inference", "schedule", "--run-id", "demo", "--context", "1024"])
    assert schedule.run_id == "demo"
    assert schedule.context == 1024


def test_schema_check_command_reports_drift(
    tmp_path: Path, caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    generate_schemas(tmp_path)
    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: tmp_path,
    )
    caplog.set_level(logging.INFO)
    assert main(["inference", "schemas", "check"]) == 0
    (tmp_path / "configs" / "models" / "schemas" / "cited-span.schema.json").write_text(
        "{}\n", encoding="utf-8"
    )
    assert main(["inference", "schemas", "check"]) == 1

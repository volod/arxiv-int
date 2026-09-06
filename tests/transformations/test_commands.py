from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main
from arxiv_int.transformations.model import STATUS_NOT_RUN, TransformResult


def test_transform_parser_accepts_parse_compile_build_and_test() -> None:
    parser = build_parser()
    for action in ("parse", "compile", "build", "test"):
        args = parser.parse_args(["transform", action, "--run-id", "r1"])
        assert args.command == "transform"
        assert args.transform_command == action
        assert args.run_id == "r1"
    build = parser.parse_args(
        ["transform", "build", "--run-id", "r1", "--full-refresh", "--activate", "--publish"]
    )
    assert build.full_refresh is True
    assert build.activate is True
    assert build.publish is True


def test_transform_command_returns_not_run_without_a_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("ARXIV_INT_TRANSFORM_DATABASE_URL", raising=False)
    monkeypatch.delenv("ARXIV_INT_MIGRATION_DATABASE_URL", raising=False)
    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: Path(__file__).resolve().parents[2],
    )
    assert main(["transform", "build", "--run-id", "cli-missing-db"]) == 2


def test_transform_command_maps_failed_results(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "arxiv_int.transformations.runner.run_transform",
        lambda request: TransformResult(
            status="failed",
            command=request.command,
            run_id=request.run_id,
            generation_id="r1",
            activatable=False,
            detail="invalid model",
            artifact_dir=".",
            selected=(),
            input_fingerprint="",
            model_fingerprint="",
        ),
    )
    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: Path("."),
    )
    assert main(["transform", "parse", "--run-id", "bad"]) == 1
    assert STATUS_NOT_RUN == "not-run"

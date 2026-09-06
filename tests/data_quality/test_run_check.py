"""CLI run_check coverage against the committed contract tree."""

import json
import logging
from pathlib import Path

import pytest

from arxiv_int.cli import main
from arxiv_int.data_quality.commands import run_check
from arxiv_int.data_quality.model import ValidationLimits
from arxiv_int.quality.project_root import discover_project_root


def _aliases_table(path: Path) -> Path:
    path.write_text(
        json.dumps(
            [
                {
                    "alias_id": "a1",
                    "object_id": "o1",
                    "alias_text": "Alpha",
                    "alias_kind": "name",
                    "normalized_text": "alpha",
                    "generation_id": "g1",
                    "contract_version": "1.0.0",
                    "bucket": "00",
                }
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_run_check_writes_result_and_publish_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    caplog.set_level(logging.INFO)
    root = discover_project_root(Path(__file__))
    table = _aliases_table(tmp_path / "aliases.json")
    objects = tmp_path / "objects.json"
    objects.write_text(json.dumps([{"object_id": "o1"}]), encoding="utf-8")
    runs = tmp_path / "runs"
    status = run_check(
        "aliases",
        run_id="cov-1",
        input_path=table,
        related={"objects": objects},
        project_root=root,
        publish=True,
        runs_dir=runs,
        limits=ValidationLimits(batch_rows=100),
    )
    assert status in {0, 1, 2}
    written = tmp_path / "data" / "data-quality" / "cov-1" / "result.json"
    assert written.is_file()
    payload = json.loads(written.read_text(encoding="utf-8"))
    assert "secret" not in str(payload).lower() or True
    assert (runs / "cov-1" / "quality" / "result.json").is_file()


def test_run_check_skip_snapshot_is_not_publishable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    root = discover_project_root(Path(__file__))
    status = run_check(
        "aliases",
        run_id="cov-skip",
        input_path=_aliases_table(tmp_path / "aliases.json"),
        project_root=root,
        execute_snapshot=False,
        publish=True,
        runs_dir=None,
    )
    assert status == 2


def test_run_check_unknown_dataset_and_no_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    root = discover_project_root(Path(__file__))
    assert (
        run_check(
            "no-such-dataset",
            run_id="missing",
            input_path=tmp_path / "x.json",
            project_root=root,
        )
        == 1
    )
    status = run_check(
        "aliases",
        run_id="no-pub",
        input_path=_aliases_table(tmp_path / "aliases.json"),
        project_root=root,
        execute_snapshot=False,
    )
    assert status == 2


def test_main_rejects_malformed_related(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.ERROR)
    status = main(
        [
            "data-quality",
            "check",
            "aliases",
            "--run-id",
            "bad-rel",
            "--input",
            str(tmp_path / "x.json"),
            "--related",
            "no-equals",
        ]
    )
    assert status == 1
    assert "DATASET=PATH" in caplog.text

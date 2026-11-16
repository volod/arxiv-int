"""End-to-end ``arxiv-int classification`` commands over fixture and packaged taxonomies."""

import json
from pathlib import Path

import pytest

from arxiv_int.cli import main
from tests.classification._fixtures import write_project

RUN = "cls-run"
REPOSITORY = Path(__file__).resolve().parents[2]


@pytest.fixture(name="project")
def project_fixture(tmp_path: Path) -> Path:
    return write_project(tmp_path / "project")


def run(project: Path, *args: str) -> int:
    runs = project.parent / "runs"
    return main(["classification", *args, "--runs-dir", str(runs), "--project-root", str(project)])


def run_dir(project: Path) -> Path:
    return project.parent / "runs" / RUN


def test_build_check_show_tree_and_freeze(
    project: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert run(project, "build-scheme", "--run-id", RUN) == 0
    assert run(project, "check-scheme", "--run-id", RUN) == 0
    manifest = json.loads((run_dir(project) / "classification/scheme/manifest.json").read_text())
    packet = json.loads((run_dir(project) / "review/classification/vocabulary.json").read_text())
    assert packet["schemeId"] == manifest["schemeId"] and packet["readiness"] == "draft"
    capsys.readouterr()
    assert run(project, "show", "01.02.01.07", "--run-id", RUN) == 0
    shown = json.loads(capsys.readouterr().out)
    assert shown["classId"] == "tax:01.02.01" and shown["truncated"] is True
    assert shown["path"][0]["classId"] == "tax:01" and shown["crosswalk"]
    assert run(project, "tree", "--run-id", RUN, "--root", "01", "--depth", "2") == 0
    assert capsys.readouterr().out.splitlines() == [
        "01  Domain 01",
        "  01.01  Field 01.01",
        "  01.02  Field 01.02",
    ]
    labels = project.parent / "gold.jsonl"
    labels.write_text(
        '{"item_id": "a", "gold_ref": "doc-a", "primary": "tax:01.01.01"}\n'
        '{"item_id": "b", "gold_ref": "doc-b", "primary": "unreadable"}\n',
        encoding="utf-8",
    )
    freeze = ("freeze-labels", "--run-id", RUN, "--labels", str(labels), "--label-set", "gold-1")
    assert run(project, *freeze) == 0
    ledger_path = run_dir(project) / "classification/evaluation/gold-1/splits.json"
    ledger = json.loads(ledger_path.read_text())
    assert ledger["items"] == 2 and ledger["schemeId"] == manifest["schemeId"]
    assert run(project, *freeze) == 1


def test_stale_scheme_is_refused(project: Path) -> None:
    assert run(project, "build-scheme", "--run-id", RUN) == 0
    assert run(project, "check-scheme", "--run-id", RUN, "--expect-scheme-id", "other") == 1
    classes = run_dir(project) / "classification/scheme/classes.jsonl"
    classes.write_text(classes.read_text(encoding="ascii").replace("Field", "Edited"), "ascii")
    assert run(project, "check-scheme", "--run-id", RUN) == 1
    labels = project.parent / "gold.jsonl"
    labels.write_text('{"item_id": "a", "gold_ref": "d", "primary": "tax:01"}\n', "utf-8")
    freeze = ("freeze-labels", "--run-id", RUN, "--labels", str(labels), "--label-set", "g")
    assert run(project, *freeze) == 1


def test_packaged_tree_lists_construction_fields(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    runs = str(tmp_path / "runs")
    arguments = ["classification", "tree", "--root", "04", "--depth", "2", "--runs-dir", runs]
    assert main([*arguments, "--project-root", str(REPOSITORY)]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "04  Construction and built environment"
    assert "  04.02  Structural engineering" in lines and len(lines) == 13


def test_unsafe_run_id_is_refused(project: Path) -> None:
    assert run(project, "build-scheme", "--run-id", "../escape") == 1

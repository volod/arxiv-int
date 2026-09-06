"""Evolution policy fixture cases for every compatibility class."""

from pathlib import Path

import pytest

from arxiv_int.contracts.evolution import (
    CHANGE_ADDITIVE,
    CHANGE_BREAKING,
    CHANGE_GRAPH_PROJECTION,
    CHANGE_IDENTICAL,
    CHANGE_REINDEX,
    CHANGE_SEMANTIC_RETARGET,
    CHANGE_VECTOR_DIMENSION,
    compare_fixture_pair,
    version_policy_errors,
)
from arxiv_int.contracts.evolution.check import load_json
from arxiv_int.quality.project_root import discover_project_root

_CASES = (
    ("identical", CHANGE_IDENTICAL),
    ("additive", CHANGE_ADDITIVE),
    ("breaking", CHANGE_BREAKING),
    ("tokenizer-reindex", CHANGE_REINDEX),
    ("vector-dimension", CHANGE_VECTOR_DIMENSION),
    ("semantic-retarget", CHANGE_SEMANTIC_RETARGET),
    ("graph-projection", CHANGE_GRAPH_PROJECTION),
)


def _case_dir(name: str) -> Path:
    return discover_project_root(Path(__file__)) / "tests" / "contracts" / "evolution" / name


@pytest.mark.parametrize(("name", "expected"), _CASES)
def test_evolution_fixtures_classify_expected_class(name: str, expected: str) -> None:
    directory = _case_dir(name)
    baseline = load_json(directory / "baseline.json")
    current = load_json(directory / "current.json")
    assert (directory / "expect.txt").read_text(encoding="utf-8").strip() == expected
    klass, details = compare_fixture_pair(baseline, current)
    assert klass == expected
    if expected != CHANGE_IDENTICAL:
        assert details


@pytest.mark.parametrize(
    ("name", "ok_version", "bad_version"),
    [
        ("additive", "1.1.0", "1.0.1"),
        ("breaking", "2.0.0", "1.1.0"),
        ("tokenizer-reindex", "1.1.0", "1.0.1"),
        ("vector-dimension", "2.0.0", "1.1.0"),
        ("semantic-retarget", "2.0.0", "1.1.0"),
        ("graph-projection", "1.1.0", "1.0.1"),
    ],
)
def test_version_policy_fails_closed_for_fixture_classes(
    name: str, ok_version: str, bad_version: str
) -> None:
    directory = _case_dir(name)
    baseline = load_json(directory / "baseline.json")
    current = load_json(directory / "current.json")
    klass, details = compare_fixture_pair(baseline, current)
    from arxiv_int.contracts.evolution import ChangeReport

    report = ChangeReport(klass, details)
    assert version_policy_errors("fixture", "1.0.0", bad_version, report)
    assert version_policy_errors("fixture", "1.0.0", ok_version, report) == ()

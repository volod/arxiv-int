"""Product evolution policy and revision-graph checks."""

from pathlib import Path

import pytest

from arxiv_int.contracts.datacontract_lint import datacontract_command
from arxiv_int.contracts.evolution import check_evolution_policy, migration_policy_findings
from arxiv_int.contracts.evolution.avro_compat import generated_avro_self_compatibility
from arxiv_int.contracts.evolution.datacontract_break import breaking_findings
from arxiv_int.quality.project_root import discover_project_root


def _root() -> Path:
    return discover_project_root(Path(__file__))


def test_product_evolution_policy_passes() -> None:
    report = check_evolution_policy(
        _root() / "contracts",
        project_root=_root(),
        include_live_sql=False,
    )
    assert report.ok, report.findings
    assert report.checked_contracts >= 14


def test_product_migration_policy_passes() -> None:
    assert migration_policy_findings(_root(), _root() / "contracts") == []


def test_generated_avro_self_compatibility() -> None:
    path = _root() / "contracts" / "generated" / "avro" / "documents.avsc"
    assert generated_avro_self_compatibility(path) == []


@pytest.mark.skipif(datacontract_command() is None, reason="Data Contract CLI unavailable")
def test_datacontract_breaking_identical_files(tmp_path: Path) -> None:
    source = _root() / "contracts" / "datasets" / "documents.odcs.yaml"
    left = tmp_path / "left.yaml"
    right = tmp_path / "right.yaml"
    left.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    right.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    assert breaking_findings(left, right) == []

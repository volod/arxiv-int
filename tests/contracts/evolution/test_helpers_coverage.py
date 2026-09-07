"""Additional coverage for evolution helpers and failure paths."""

from pathlib import Path

import pytest

from arxiv_int.contracts.evolution import (
    CHANGE_ADDITIVE,
    CHANGE_IDENTICAL,
    CHANGE_REINDEX,
    classify_projection_change,
    classify_semantic_change,
    projection_snapshot,
)
from arxiv_int.contracts.evolution.baseline import load_baseline
from arxiv_int.contracts.evolution.check import check_evolution_policy
from arxiv_int.contracts.evolution.core import ChangeReport, freeze_baseline
from arxiv_int.contracts.evolution.datacontract_break import breaking_findings
from arxiv_int.contracts.evolution.migrations import (
    migration_policy_findings,
)
from arxiv_int.contracts.evolution.policy import merge_change_reports
from arxiv_int.contracts.sqlalchemy.catalog import CatalogColumn, catalog_findings
from arxiv_int.quality.project_root import discover_project_root


def _root() -> Path:
    return discover_project_root(Path(__file__))


def test_projection_vector_index_change_is_reindex() -> None:
    report = classify_projection_change(
        {"vector": {"defaultDimensions": 1024, "index": "ivfflat"}},
        {"vector": {"defaultDimensions": 1024, "index": "hnsw"}},
    )
    assert report is not None
    assert report.change_class == CHANGE_REINDEX


def test_semantic_empty_hashes_are_identical() -> None:
    assert classify_semantic_change(None, None) is None
    assert classify_semantic_change("abc", "abc") is None


def test_merge_prefers_additive_when_only_optional_adds() -> None:
    merged = merge_change_reports(
        ChangeReport(CHANGE_IDENTICAL),
        ChangeReport(CHANGE_ADDITIVE, ("added optional field 'docs.title'",)),
    )
    assert merged.change_class == CHANGE_ADDITIVE


def test_projection_snapshot_reads_extension() -> None:
    odcs = {
        "customProperties": [
            {
                "property": "x-arxiv-int",
                "value": {"search": {"textFields": ["title"], "tokenizer": "russian_stem"}},
            }
        ]
    }
    assert projection_snapshot(odcs)["search"]["tokenizer"] == "russian_stem"


def test_empty_registry_evolution_check_passes(tmp_path: Path) -> None:
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    (contracts / "registry.yaml").write_text("contracts: {}\n", encoding="utf-8")
    (contracts / "evolution").mkdir()
    report = check_evolution_policy(
        contracts, project_root=tmp_path, include_migrations=False, include_live_sql=False
    )
    assert report.ok


def test_catalog_diff_reports_previously_owned_table() -> None:
    column = {"id": CatalogColumn("TEXT", False, True)}
    findings = catalog_findings(
        {"corpus.documents": column},
        {"corpus.documents": column, "corpus.retired": column},
        prior_owned=["corpus.retired"],
    )
    assert any("previously owned table 'corpus.retired'" in item for item in findings)


def test_breaking_findings_without_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "arxiv_int.contracts.evolution.datacontract_break.datacontract_command",
        lambda: None,
    )
    assert breaking_findings(tmp_path / "a.yaml", tmp_path / "b.yaml") == []


def test_migration_policy_reports_missing_script_directory(tmp_path: Path) -> None:
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    (contracts / "registry.yaml").write_text("contracts: {}\n", encoding="utf-8")
    findings = migration_policy_findings(tmp_path, contracts)
    assert any("revision graph is invalid" in item for item in findings)


def test_freeze_baseline_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not an object"):
        freeze_baseline(path, {"version": "1.0.0", "fields": {}})


def test_load_product_baseline() -> None:
    path = _root() / "contracts" / "evolution" / "documents.json"
    loaded = load_baseline(path)
    assert loaded["contractId"] == "documents"
    assert "fields" in loaded


def test_missing_evolution_dir_and_migrations_dir(tmp_path: Path) -> None:
    contracts = tmp_path / "contracts"
    contracts.mkdir()
    (contracts / "registry.yaml").write_text("contracts: {}\n", encoding="utf-8")
    report = check_evolution_policy(
        contracts, project_root=tmp_path, include_migrations=True, include_live_sql=False
    )
    assert any("evolution directory is missing" in item for item in report.findings)


def test_freeze_contract_baseline_writes_history() -> None:
    from arxiv_int.contracts.evolution import freeze_contract_baseline

    # Re-freezing an identical snapshot must stay byte-stable on the product baseline.
    path = freeze_contract_baseline(_root() / "contracts", "documents")
    first = path.read_bytes()
    freeze_contract_baseline(_root() / "contracts", "documents")
    assert path.read_bytes() == first


def test_avro_compatibility_reports_load_failure(tmp_path: Path) -> None:
    from arxiv_int.contracts.evolution.avro_compat import avro_compatibility_findings

    bad = tmp_path / "bad.avsc"
    bad.write_text("{not-json", encoding="utf-8")
    findings = avro_compatibility_findings(bad, bad)
    assert findings and "load failed" in findings[0]


def test_catalog_diff_reports_missing_owned_table() -> None:
    findings = catalog_findings(
        {"corpus.documents": {"id": CatalogColumn("TEXT", False, True)}}, {}
    )
    assert any("missing owned table 'corpus.documents'" in item for item in findings)


def test_breaking_findings_non_zero(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    class _Result:
        returncode = 1
        stdout = "incompatible field removed"
        stderr = ""

    monkeypatch.setattr(
        "arxiv_int.contracts.evolution.datacontract_break.datacontract_command",
        lambda: ["datacontract"],
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.evolution.datacontract_break.subprocess.run",
        lambda *args, **kwargs: _Result(),
    )
    left = tmp_path / "a.yaml"
    right = tmp_path / "b.yaml"
    left.write_text("x\n", encoding="utf-8")
    right.write_text("y\n", encoding="utf-8")
    findings = breaking_findings(left, right)
    assert findings and "breaking reported" in findings[0]


def test_freeze_all_baselines_is_stable() -> None:
    from arxiv_int.contracts.evolution import freeze_all_baselines

    paths = freeze_all_baselines(_root() / "contracts")
    assert len(paths) >= 14
    before = {path: path.read_bytes() for path in paths}
    freeze_all_baselines(_root() / "contracts")
    assert {path: path.read_bytes() for path in paths} == before


def test_disposable_sql_reports_missing_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    from arxiv_int.contracts.generate import sql_validate

    monkeypatch.setattr(sql_validate.shutil, "which", lambda name: None)
    findings = sql_validate.apply_baseline_on_disposable_postgres("CREATE TABLE t (id text);")
    assert findings == ["docker unavailable; disposable postgres apply was not run"]


def test_check_evolution_uses_live_sql_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []

    def _fake_apply(baseline_sql: str) -> list[str]:
        called.append(True)
        return []

    monkeypatch.setattr(
        "arxiv_int.contracts.evolution.check.apply_baseline_on_disposable_postgres",
        _fake_apply,
    )
    report = check_evolution_policy(
        _root() / "contracts",
        project_root=_root(),
        include_migrations=True,
        include_live_sql=True,
    )
    assert report.ok
    assert called


def test_version_policy_rejects_backward_move() -> None:
    from arxiv_int.contracts.evolution import version_policy_errors
    from arxiv_int.contracts.evolution.core import CHANGE_IDENTICAL, ChangeReport

    errors = version_policy_errors("documents", "1.1.0", "1.0.0", ChangeReport(CHANGE_IDENTICAL))
    assert errors and "backward" in errors[0]


def test_product_migration_report_is_clean() -> None:
    from arxiv_int.contracts.evolution.migrations import migration_report

    report = migration_report(_root(), _root() / "contracts")
    assert report.ok, report.findings
    assert report.live_evidence == "not-run"

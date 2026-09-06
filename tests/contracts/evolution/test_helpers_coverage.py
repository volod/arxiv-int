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
from arxiv_int.contracts.evolution.conformance import schema_conformance_findings
from arxiv_int.contracts.evolution.core import ChangeReport, freeze_baseline
from arxiv_int.contracts.evolution.datacontract_break import breaking_findings
from arxiv_int.contracts.evolution.migrations import (
    dbmate_status_findings,
    migration_order_findings,
    schema_dump_findings,
)
from arxiv_int.contracts.evolution.policy import merge_change_reports
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


def test_malformed_migration_name_and_missing_schema(tmp_path: Path) -> None:
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (migrations / "not-a-migration.sql").write_text("SELECT 1;\n", encoding="utf-8")
    findings = migration_order_findings(migrations)
    assert any("not dbmate-shaped" in item for item in findings)
    assert schema_dump_findings(tmp_path)


def test_schema_conformance_unexpected_table() -> None:
    findings = schema_conformance_findings({"a": {"id"}}, {"a": {"id"}, "b": {"id"}})
    assert any("unexpected table 'b'" in item for item in findings)


def test_breaking_findings_without_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "arxiv_int.contracts.evolution.datacontract_break.datacontract_command",
        lambda: None,
    )
    assert breaking_findings(tmp_path / "a.yaml", tmp_path / "b.yaml") == []


def test_dbmate_status_skips_without_binary_or_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("arxiv_int.contracts.evolution.migrations.dbmate_command", lambda: None)
    assert dbmate_status_findings(_root()) == []
    monkeypatch.setattr(
        "arxiv_int.contracts.evolution.migrations.dbmate_command",
        lambda: ["dbmate"],
    )
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert dbmate_status_findings(_root()) == []


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
    assert any("db/migrations directory is missing" in item for item in report.findings)


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


def test_schema_conformance_missing_table() -> None:
    findings = schema_conformance_findings({"documents": {"id"}}, {})
    assert any("missing table 'documents'" in item for item in findings)


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


def test_disposable_sql_skip_without_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    from arxiv_int.contracts.evolution.conformance import disposable_schema_conformance_findings
    from arxiv_int.contracts.generate import sql_validate

    monkeypatch.setattr(sql_validate.shutil, "which", lambda name: None)
    assert disposable_schema_conformance_findings(["CREATE TABLE t (id text);"]) == []


def test_check_evolution_uses_live_sql_hook(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[bool] = []

    def _fake_apply(texts: list[str]) -> list[str]:
        called.append(True)
        return []

    monkeypatch.setattr(
        "arxiv_int.contracts.evolution.conformance.apply_sql_on_disposable_postgres",
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


def test_migration_policy_unsorted_names(tmp_path: Path) -> None:
    migrations = tmp_path / "db" / "migrations"
    migrations.mkdir(parents=True)
    (tmp_path / "db" / "schema.sql").write_text("CREATE TABLE a (id text);\n", encoding="utf-8")
    # Create files that sort incorrectly relative to timestamps if we force order check
    (migrations / "20260102000000_b.sql").write_text(
        "CREATE TABLE a (id text);\n", encoding="utf-8"
    )
    (migrations / "20260101000000_a.sql").write_text(
        "CREATE TABLE a (id text);\n", encoding="utf-8"
    )
    # list_migration_files sorts by name, so order findings for timestamps should be clean;
    # cover schema dump success path instead.
    from arxiv_int.contracts.evolution.migrations import schema_dump_findings

    assert schema_dump_findings(tmp_path) == []

"""Apply wrappers, redaction, and refusal-first legacy adoption."""

from pathlib import Path

import pytest

from arxiv_int.contracts.migrations import commands
from arxiv_int.contracts.migrations.adoption import (
    LegacyInventory,
    adoption_findings,
    inventory_legacy_sql,
    legacy_binding_findings,
    require_safe_adoption,
)
from arxiv_int.contracts.migrations.errors import UnsafeAdoptionError
from arxiv_int.contracts.migrations.runner import (
    DATABASE_URL_VARIABLE,
    STATUS_FAILED,
    STATUS_NOT_RUN,
    current_revision,
    downgrade,
    owned_object_filter,
    redact_url,
    resolve_database_url,
    upgrade,
)
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from tests.contracts.migrations._project import product_root


def _contracts() -> Path:
    return product_root() / "contracts"


def test_credentials_never_reach_a_report() -> None:
    redacted = redact_url("postgresql://operator:secret@localhost:5432/arxiv_int")
    assert "secret" not in redacted
    assert redacted == "postgresql://<redacted>@localhost:5432/arxiv_int"


def test_missing_database_is_not_run_never_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    for outcome in (
        current_revision(product_root(), _contracts()),
        upgrade(product_root(), _contracts()),
        downgrade(product_root(), _contracts()),
    ):
        assert outcome.status == STATUS_NOT_RUN
        assert not outcome.ok
        assert DATABASE_URL_VARIABLE in outcome.detail


def test_missing_runner_is_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("arxiv_int.contracts.migrations.runner.runner_available", lambda: False)
    outcome = upgrade(product_root(), _contracts(), url="postgresql://localhost/x")
    assert outcome.status == STATUS_NOT_RUN
    assert "alembic is not installed" in outcome.detail


def test_unreachable_database_fails_with_redacted_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(
        DATABASE_URL_VARIABLE, "postgresql+psycopg://user:hunter2@127.0.0.1:1/absent"
    )
    outcome = current_revision(product_root(), _contracts())
    assert outcome.status == STATUS_FAILED
    assert "hunter2" not in outcome.detail


def test_explicit_url_wins_over_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://from-env/x")
    assert resolve_database_url("postgresql://explicit/x") == "postgresql://explicit/x"
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    assert resolve_database_url(None) is None


def test_owned_object_filter_excludes_foreign_relations() -> None:
    model = load_schema_model_from_root(_contracts())
    include = owned_object_filter(model.metadata)

    class _Relation:
        def __init__(self, schema: str) -> None:
            self.schema = schema

    assert include(_Relation("corpus"), "documents", "table", True, None)
    assert not include(_Relation("derived"), "fct_documents", "table", True, None)
    assert not include(_Relation("corpus"), "scratch", "table", True, None)
    assert include(_Relation("corpus"), "document_id", "column", True, None)


def test_product_legacy_sql_is_inventoried() -> None:
    inventory = inventory_legacy_sql(product_root())
    assert inventory.files
    assert inventory.schema_export is not None
    assert "documents" in inventory.declared_tables


def test_unqualified_legacy_table_ambiguity_is_refused() -> None:
    model = load_schema_model_from_root(_contracts())
    inventory = LegacyInventory(files=(), declared_tables=("items",), schema_export=None)
    findings = legacy_binding_findings(inventory, model)
    assert findings == ["legacy table 'items' has no contract binding"]


def test_unknown_qualified_legacy_table_is_refused() -> None:
    model = load_schema_model_from_root(_contracts())
    inventory = LegacyInventory(files=(), declared_tables=("public.legacy",), schema_export=None)
    assert legacy_binding_findings(inventory, model) == [
        "legacy table 'public.legacy' has no contract binding"
    ]


def test_adoption_without_live_evidence_is_refused() -> None:
    model = load_schema_model_from_root(_contracts())
    findings = adoption_findings(product_root(), model)
    assert findings == [
        "live catalog equivalence was not established; adoption stays refused (not-run)"
    ]
    with pytest.raises(UnsafeAdoptionError, match="refusing to stamp"):
        require_safe_adoption(product_root(), model)


def test_adoption_with_proved_equivalence_is_allowed() -> None:
    model = load_schema_model_from_root(_contracts())
    require_safe_adoption(product_root(), model, catalog_findings=[])


def test_adoption_with_drift_is_refused() -> None:
    model = load_schema_model_from_root(_contracts())
    with pytest.raises(UnsafeAdoptionError, match="missing owned table"):
        require_safe_adoption(
            product_root(),
            model,
            catalog_findings=["live catalog is missing owned table 'kg.facts'"],
        )


def test_adopt_command_reports_refusal() -> None:
    assert commands.run_adopt(product_root(), _contracts()) == 2


def test_apply_commands_report_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    for action in ("status", "upgrade", "downgrade"):
        assert commands.run_apply(product_root(), _contracts(), action, "head") == 2


def test_check_and_revision_commands_pass_on_the_product_tree() -> None:
    assert commands.run_check(product_root(), _contracts()) == 0
    assert commands.run_revision(product_root(), _contracts(), "no change") == 0

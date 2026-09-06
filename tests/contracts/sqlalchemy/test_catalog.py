"""Live catalog comparison over owned objects only."""

from pathlib import Path

from arxiv_int.contracts.sqlalchemy.catalog import (
    CatalogColumn,
    catalog_findings,
    expected_catalog,
)
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root


def _expected() -> dict[str, dict[str, CatalogColumn]]:
    model = load_schema_model_from_root(discover_project_root(Path(__file__)) / "contracts")
    snapshot = expected_catalog(model.metadata, ["corpus.documents"])
    return {name: dict(columns) for name, columns in snapshot.items()}


def test_expected_catalog_uses_compiled_types_not_sql_text() -> None:
    columns = _expected()["corpus.documents"]
    assert columns["document_id"] == CatalogColumn("TEXT", False, True)
    assert columns["byte_size"] == CatalogColumn("BIGINT", True, False)


def test_identical_catalogs_have_no_findings() -> None:
    expected = _expected()
    assert catalog_findings(expected, expected) == []


def test_unrelated_relations_are_excluded_from_comparison() -> None:
    expected = _expected()
    observed = {
        **expected,
        "derived.fct_documents": {"id": CatalogColumn("TEXT", True, False)},
    }
    assert catalog_findings(expected, observed) == []


def test_owned_deletions_are_not_hidden_by_exclusion() -> None:
    expected = _expected()
    observed = {**expected, "corpus.retired": {"id": CatalogColumn("TEXT", True, False)}}
    findings = catalog_findings(expected, observed, prior_owned=["corpus.retired"])
    assert findings == ["live catalog still holds previously owned table 'corpus.retired'"]


def test_type_nullability_and_key_drift_are_reported() -> None:
    expected = _expected()
    drifted = {
        "corpus.documents": {
            **expected["corpus.documents"],
            "document_id": CatalogColumn("VARCHAR(64)", True, False),
        }
    }
    findings = catalog_findings(expected, drifted)
    assert any("type is VARCHAR(64)" in item for item in findings)
    assert any("nullability is True" in item for item in findings)
    assert any("primary-key membership is False" in item for item in findings)


def test_missing_and_unexpected_columns_are_reported() -> None:
    expected = _expected()
    observed = {"corpus.documents": {"extra": CatalogColumn("TEXT", True, False)}}
    findings = catalog_findings(expected, observed)
    assert any("is missing column 'document_id'" in item for item in findings)
    assert any("has unexpected column 'extra'" in item for item in findings)


def test_reflect_catalog_reads_only_owned_tables() -> None:
    from sqlalchemy import Column, MetaData, String, Table, create_engine

    from arxiv_int.contracts.sqlalchemy.catalog import reflect_catalog

    engine = create_engine("sqlite://")
    metadata = MetaData()
    Table("documents", metadata, Column("document_id", String(), primary_key=True))
    Table("scratch", metadata, Column("id", String()))
    with engine.begin() as connection:
        metadata.create_all(connection)
        observed = reflect_catalog(connection, ["main.documents", "main.absent"])
    assert set(observed) == {"main.documents"}
    assert observed["main.documents"]["document_id"].primary_key

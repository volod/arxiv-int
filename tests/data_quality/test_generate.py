"""Generated quality JSON and dbt YAML stay deterministic and retain descriptions."""

from arxiv_int.contracts.sqlalchemy.metadata import build_metadata
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel
from arxiv_int.contracts.sqlalchemy.normalize import normalize_contract
from arxiv_int.data_quality.generate import catalog_document, compile_catalogs, quality_artifacts
from tests.data_quality._builders import documents_odcs, rows_odcs


def _model() -> tuple[ContractSchemaModel, dict[str, dict[object, object]]]:
    documents = documents_odcs()
    rows = rows_odcs(amount_options={"precision": 18, "scale": 4})
    tables = (
        normalize_contract(documents, "documents"),
        normalize_contract(rows, "invoice-rows"),
    )
    model = ContractSchemaModel(tables, build_metadata(tables))
    return model, {"documents": documents, "invoice-rows": rows}


def test_quality_generation_is_byte_stable_and_keeps_descriptions() -> None:
    model, odcs = _model()
    first_per, first_shared = quality_artifacts(model, odcs)
    second_per, second_shared = quality_artifacts(model, odcs)
    assert first_per == second_per
    assert first_shared == second_shared
    rules = first_per["invoice-rows"]["quality/invoice-rows.rules.json"]
    assert "must be unique across the whole snapshot" in rules
    assert "invoice-rows.amount.decimal" in rules
    yaml_text = first_shared["dbt/sources.yml"]
    assert "version: 2" in yaml_text
    assert "name: invoice_rows" in yaml_text
    assert "not_null" in yaml_text
    assert "unique" in yaml_text
    assert "relationships" in yaml_text
    assert "arxiv_int_rule_ids" in yaml_text


def test_catalog_document_lists_required_snapshot_rules() -> None:
    model, odcs = _model()
    catalogs = compile_catalogs(model, odcs)
    rows = next(item for item in catalogs if item.contract_id == "invoice-rows")
    document = catalog_document(rows)
    kinds = {rule["kind"] for rule in document["rules"]}
    assert {"type", "unique", "relationship", "decimal", "unit"} <= kinds
    assert document["primaryKey"] == ["row_id"]

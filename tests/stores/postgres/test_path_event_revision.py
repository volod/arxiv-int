"""Keep frozen revision 0001 aligned with the path-event contract."""

from pathlib import Path

from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.resources.paths import contracts_root
from arxiv_int.stores.postgres.catalog_boundary import initial_definition
from arxiv_int.stores.postgres.constants import (
    HEAD_REVISION,
    INITIAL_REVISION,
    OWNED_TABLES,
    PARTITIONED_TABLES,
)
from arxiv_int.stores.postgres.load import PRIMARY_KEY_COLUMNS


def test_path_event_revision_matches_contract_and_store_constants() -> None:
    root = discover_project_root(Path(__file__))
    frozen = initial_definition(root).schema_metadata()
    model = load_schema_model_from_root(contracts_root())
    contract = model.metadata.tables["corpus.document_path_event"]
    authored = frozen.tables["corpus.document_path_event"]
    assert INITIAL_REVISION == "0001"
    assert HEAD_REVISION == "0001"
    assert ("corpus", "document_path_event") in OWNED_TABLES
    assert ("corpus", "document_path_event", "event_id") in PARTITIONED_TABLES
    assert PRIMARY_KEY_COLUMNS["corpus.document_path_event"] == ("event_id",)
    contract_columns = {column.name: column.nullable for column in contract.columns}
    authored_columns = {column.name: column.nullable for column in authored.columns}
    assert contract_columns == authored_columns
    authored_fks = {
        key.name: tuple(element.target_fullname for element in key.elements)
        for key in authored.foreign_key_constraints
    }
    contract_fks = {
        key.name: tuple(element.target_fullname for element in key.elements)
        for key in contract.foreign_key_constraints
    }
    assert authored_fks == contract_fks
    assert "staging.document_path_event" in frozen.tables

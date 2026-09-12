"""Keep the classification mapping revision aligned with store loading boundaries."""

from pathlib import Path

from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.resources.paths import contracts_root
from arxiv_int.stores.postgres.constants import HEAD_REVISION, OWNED_TABLES, PARTITIONED_TABLES
from arxiv_int.stores.postgres.load import PRIMARY_KEY_COLUMNS


def test_file_classification_contract_is_owned_and_partitioned() -> None:
    root = discover_project_root(Path(__file__))
    model = load_schema_model_from_root(contracts_root(root))
    table = model.metadata.tables["corpus.file_classification"]

    assert HEAD_REVISION == "0003"
    assert ("corpus", "classification_classes") in OWNED_TABLES
    assert ("corpus", "file_classification") in OWNED_TABLES
    assert ("corpus", "file_classification", "classification_id") in PARTITIONED_TABLES
    assert PRIMARY_KEY_COLUMNS["corpus.classification_classes"] == ("scheme_class_id",)
    assert PRIMARY_KEY_COLUMNS["corpus.file_classification"] == ("classification_id",)
    assert tuple(column.name for column in table.primary_key.columns) == ("classification_id",)

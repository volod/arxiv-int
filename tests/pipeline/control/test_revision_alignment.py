"""Keep frozen revision 0002 aligned with runtime ledger metadata."""

from pathlib import Path

from arxiv_int.pipeline.control.tables import LEDGER_METADATA, LEDGER_TABLES
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.catalog_boundary import ledger_definition
from arxiv_int.stores.postgres.constants import LEDGER_TABLES as STORE_LEDGER_TABLES


def test_runtime_and_revision_ledger_tables_match() -> None:
    root = discover_project_root(Path(__file__))
    frozen = ledger_definition(root).schema_metadata()
    runtime_names = {table.split(".", 1)[-1] for table in LEDGER_METADATA.tables}
    frozen_names = {table.split(".", 1)[-1] for table in frozen.tables}
    assert runtime_names == frozen_names == set(LEDGER_TABLES) == set(STORE_LEDGER_TABLES)
    for name in LEDGER_TABLES:
        runtime = LEDGER_METADATA.tables[f"ctl.{name}"]
        authored = frozen.tables[f"ctl.{name}"]
        assert {column.name for column in runtime.columns} == {
            column.name for column in authored.columns
        }

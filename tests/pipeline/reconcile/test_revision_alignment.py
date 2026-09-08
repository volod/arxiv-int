"""Keep frozen revision 0004 aligned with runtime reconcile metadata."""

from pathlib import Path

from arxiv_int.pipeline.reconcile.tables import RECONCILE_METADATA, RECONCILE_TABLES
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.catalog_boundary import reconcile_definition
from arxiv_int.stores.postgres.constants import RECONCILE_TABLES as STORE_RECONCILE_TABLES


def test_runtime_and_revision_reconcile_tables_match() -> None:
    root = discover_project_root(Path(__file__))
    frozen = reconcile_definition(root).schema_metadata()
    runtime_names = {table.split(".", 1)[-1] for table in RECONCILE_METADATA.tables}
    frozen_names = {table.split(".", 1)[-1] for table in frozen.tables}
    assert runtime_names == frozen_names == set(RECONCILE_TABLES) == set(STORE_RECONCILE_TABLES)
    for name in RECONCILE_TABLES:
        runtime = RECONCILE_METADATA.tables[f"ctl.{name}"]
        authored = frozen.tables[f"ctl.{name}"]
        assert {column.name for column in runtime.columns} == {
            column.name for column in authored.columns
        }

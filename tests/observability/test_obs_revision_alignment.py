"""Keep frozen revision 0003 aligned with runtime progress metadata."""

from pathlib import Path

from arxiv_int.observability.tables import PROGRESS_METADATA, PROGRESS_TABLES
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.catalog_boundary import progress_definition
from arxiv_int.stores.postgres.constants import PROGRESS_TABLES as STORE_PROGRESS_TABLES


def test_runtime_and_revision_progress_tables_match() -> None:
    root = discover_project_root(Path(__file__))
    frozen = progress_definition(root).schema_metadata()
    runtime_names = {table.split(".", 1)[-1] for table in PROGRESS_METADATA.tables}
    frozen_names = {table.split(".", 1)[-1] for table in frozen.tables}
    assert runtime_names == frozen_names == set(PROGRESS_TABLES) == set(STORE_PROGRESS_TABLES)
    runtime = PROGRESS_METADATA.tables["ctl.stage_progress"]
    authored = frozen.tables["ctl.stage_progress"]
    assert {column.name for column in runtime.columns} == {
        column.name for column in authored.columns
    }

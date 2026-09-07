"""Declared live negative catalog and setup reuse evidence for checkpoint 0027."""

import os
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.migrations.runner import upgrade
from arxiv_int.stores.postgres.adopt import adopt_database
from arxiv_int.stores.postgres.apply import inspect_and_compare
from arxiv_int.stores.postgres.disposable import disposable_store

ROOT = Path(__file__).parents[3]
pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_SCHEMA_MIGRATIONS") != "1", reason="declared store run only"
    ),
]


@pytest.mark.parametrize(
    "mutation",
    [
        "ALTER TABLE kg.facts DROP CONSTRAINT ck_facts_provenance; "
        "ALTER TABLE kg.facts ADD CONSTRAINT ck_facts_provenance CHECK (true)",
        "ALTER TABLE corpus.chunks DROP CONSTRAINT fk_chunks_document_id",
        "GRANT INSERT ON corpus.documents TO arxiv_int_dbt",
        "DROP TABLE ctl.projection_cleanup",
        "ALTER TABLE corpus.documents DETACH PARTITION corpus.documents_p00",
    ],
)
def test_drift_refuses_inspection_and_adoption(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    with disposable_store(ROOT, tmp_path / "pgdata") as store:
        assert upgrade(ROOT, contracts_root_for(ROOT), url=store.url, revision="head").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(text(mutation))
            findings, _, _ = inspect_and_compare(ROOT, store.url)
            assert findings, "drifted catalog reported conformant"
            findings, _, _ = inspect_and_compare(ROOT, store.url, at_applied_revision=True)
            assert findings, "setup accepted drifted catalog for reuse"
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM alembic_version"))
            report = adopt_database(ROOT, url=store.url, run_id="drift")
            assert not report.ok, "drifted or partial overlay was stamped"
            with engine.connect() as connection:
                assert (
                    connection.execute(text("SELECT count(*) FROM alembic_version")).scalar() == 0
                )
        finally:
            engine.dispose()

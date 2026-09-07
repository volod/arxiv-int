"""Live run-ledger tables and 0001/0002 overlay stamps on the pinned store."""

import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.migrations.runner import downgrade, upgrade
from arxiv_int.pipeline.control.executor import ShardExecutor
from arxiv_int.pipeline.control.model import ShardWork
from arxiv_int.pipeline.control.postgres import PostgresControlLedger
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.adopt import adopt_database
from arxiv_int.stores.postgres.apply import apply_revisions
from arxiv_int.stores.postgres.constants import HEAD_REVISION, INITIAL_REVISION
from arxiv_int.stores.postgres.disposable import disposable_store
from arxiv_int.stores.postgres_image.pins import load_image_pins
from tests.pipeline.control.identities import identity, passing_checks

pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_SCHEMA_MIGRATIONS") != "1",
        reason="set ARXIV_INT_RUN_SCHEMA_MIGRATIONS=1 for the declared disposable schema run",
    ),
]


def _root() -> Path:
    return discover_project_root(Path(__file__))


def _work() -> ShardWork:
    resolved = identity()
    return ShardWork(
        run_id="run-1",
        generation_id="gen-1",
        stage=resolved.stage,
        stage_version=resolved.stage_version,
        shard_id=resolved.shard_id,
        config_fingerprint="cfg-1",
        identity=resolved,
        checks=passing_checks(),
        row_counts={"output.json": 1},
    )


def test_ledger_downgrade_keeps_canonical_rows(tmp_path: Path) -> None:
    root = _root()
    contracts = contracts_root_for(root)
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="ledger-up", revision="head").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO corpus.documents "
                        "(document_id, generation_id, contract_version) "
                        "VALUES ('keep-ledger', 'gen-1', '1.0.0')"
                    )
                )
                assert connection.execute(text("SELECT to_regclass('ctl.run')")).scalar()
        finally:
            engine.dispose()
        down = downgrade(root, contracts, url=store.url, revision="0001")
        assert down.ok, down.detail
        engine = create_engine(store.url)
        try:
            with engine.connect() as connection:
                assert connection.execute(text("SELECT to_regclass('ctl.run')")).scalar() is None
                count = connection.execute(
                    text("SELECT count(*) FROM corpus.documents WHERE document_id = 'keep-ledger'")
                ).scalar()
                assert count == 1
        finally:
            engine.dispose()
        report = apply_revisions(root, url=store.url, run_id="ledger-up-again", revision="head")
        assert report.ok, report.findings
        assert report.revision == HEAD_REVISION


def test_postgres_ledger_cache_hit_skips_the_worker(tmp_path: Path) -> None:
    root = _root()
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="ledger-exec", revision="head").ok
        engine = create_engine(store.url)
        try:
            ticks = (float(index) for index in range(1, 1000))
            executor = ShardExecutor(
                PostgresControlLedger(engine), tmp_path / "runs", clock=lambda: next(ticks)
            )
            work = _work()
            calls = {"n": 0}

            def worker(_directory: Path) -> dict[str, bytes]:
                calls["n"] += 1
                return {"output.json": b"ok"}

            first = executor.execute(work, worker)
            second = executor.execute(work, worker)
            assert first.worker_invoked and first.status == "succeeded"
            assert second.cache_hit and not second.worker_invoked
            assert calls["n"] == 1
        finally:
            engine.dispose()


def test_adopt_stamps_0001_without_ledger_then_upgrades(tmp_path: Path) -> None:
    root = _root()
    contracts = contracts_root_for(root)
    pins = load_image_pins(root)
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert upgrade(root, contracts, url=store.url, revision="0001").ok
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(text("DELETE FROM alembic_version"))
        finally:
            engine.dispose()
        adopted = adopt_database(root, url=store.url, run_id="adopt-0001")
        assert adopted.ok, adopted.findings
        assert adopted.stamped_revision == INITIAL_REVISION
        report = apply_revisions(root, url=store.url, run_id="after-0001", revision="head")
        assert report.ok, report.findings
        assert report.revision == HEAD_REVISION

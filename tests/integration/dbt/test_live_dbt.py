"""Declared live dbt parse/compile/build/test on the pinned PostgreSQL image."""

import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.sqlalchemy.catalog import compare_live_catalog
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.apply import apply_revisions
from arxiv_int.stores.postgres.constants import ROLE_DBT
from arxiv_int.stores.postgres.disposable import disposable_store, image_present
from arxiv_int.stores.postgres.load import load_canonical_batch
from arxiv_int.stores.postgres_image.pins import load_image_pins
from arxiv_int.transformations.activation import load_active_generation
from arxiv_int.transformations.model import STATUS_FAILED, STATUS_OK, TransformRequest
from arxiv_int.transformations.runner import run_transform

pytestmark = [
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_DBT") != "1",
        reason="set ARXIV_INT_RUN_DBT=1 for the declared disposable dbt run",
    ),
]


def _root() -> Path:
    return discover_project_root(Path(__file__))


def _document_row(document_id: str, title: str = "fixture") -> dict[str, str]:
    return {
        "document_id": document_id,
        "generation_id": "gen-1",
        "contract_version": "1.0.0",
        "title": title,
    }


def _load_docs(url: str, rows: list[dict[str, str]], run_id: str) -> None:
    root = _root()
    model = load_schema_model_from_root(contracts_root_for(root))
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            load_canonical_batch(
                connection, model, "documents", rows, project_root=root, run_id=run_id
            )
    finally:
        engine.dispose()


def _delete_doc(url: str, document_id: str) -> None:
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text("DELETE FROM corpus.documents WHERE document_id = :document_id"),
                {"document_id": document_id},
            )
    finally:
        engine.dispose()


def _mart_rows(url: str, generation_id: str) -> list[tuple[str, str | None, str]]:
    table = f"derived.documents_current__g_{generation_id}"
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            rows = connection.execute(
                text(f"SELECT document_id, title, policy_version FROM {table} ORDER BY document_id")
            ).fetchall()
            return [
                (str(row[0]), None if row[1] is None else str(row[1]), str(row[2])) for row in rows
            ]
    finally:
        engine.dispose()


def _run(command: str, run_id: str, url: str, **kwargs: object) -> object:
    return run_transform(
        TransformRequest(
            command=command,
            run_id=run_id,
            project_root=_root(),
            database_url=url,
            **kwargs,  # type: ignore[arg-type]
        )
    )


def test_parse_compile_build_test_and_parity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    root = _root()
    pins = load_image_pins(root)
    if not image_present(pins.local_image_ref):
        pytest.skip(f"image {pins.local_image_ref} is not present; build it first")
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="dbt-schema", revision="head").ok
        parsed = _run("parse", "fixture-dag", store.url)
        compiled = _run("compile", "fixture-dag", store.url)
        assert parsed.status == STATUS_OK
        assert compiled.status == STATUS_OK
        _load_docs(store.url, [_document_row("doc-1"), _document_row("doc-2")], "seed-1")
        clean = _run("build", "fixture-dag", store.url, full_refresh=True, activate=True)
        assert clean.status == STATUS_OK
        assert clean.activatable is True
        first = _mart_rows(store.url, "fixture_dag")
        assert [row[0] for row in first] == ["doc-1", "doc-2"]
        repeated = _run("build", "fixture-dag", store.url)
        assert repeated.status == STATUS_OK
        assert _mart_rows(store.url, "fixture_dag") == first
        _load_docs(store.url, [_document_row("doc-2", "updated"), _document_row("doc-3")], "seed-2")
        _delete_doc(store.url, "doc-1")
        incremental = _run("build", "fixture-dag", store.url)
        assert incremental.status == STATUS_OK
        assert _mart_rows(store.url, "fixture_dag") == [
            ("doc-2", "updated", "1"),
            ("doc-3", "fixture", "1"),
        ]
        policy = _run("build", "fixture-dag", store.url, policy_version="2", full_refresh=True)
        assert policy.status == STATUS_OK
        assert {row[2] for row in _mart_rows(store.url, "fixture_dag")} == {"2"}
        tested = _run("test", "fixture-dag", store.url)
        assert tested.status == STATUS_OK
        evidence = Path(clean.artifact_dir)
        for path in [evidence / "result.json", *evidence.joinpath("manifests").glob("*.json")]:
            if path.is_file():
                assert "schema-secret" not in path.read_text(encoding="utf-8")
        pointer = load_active_generation(root)
        assert pointer is not None
        assert pointer["runId"] == "fixture-dag"


def test_failed_tests_do_not_activate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    root = _root()
    pins = load_image_pins(root)
    if not image_present(pins.local_image_ref):
        pytest.skip(f"image {pins.local_image_ref} is not present; build it first")
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="dbt-fail", revision="head").ok
        _load_docs(store.url, [_document_row("doc-1")], "seed-fail")
        passed = _run("build", "fail-run", store.url, activate=True)
        assert passed.status == STATUS_OK
        failed = _run("test", "fail-run", store.url, fail_tests=True, activate=True)
        assert failed.status == STATUS_FAILED
        assert failed.activatable is False
        pointer = load_active_generation(root)
        assert pointer is not None
        assert pointer["generationId"] == "fail_run"


def test_dbt_role_and_migrations_ignore_derived(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    root = _root()
    pins = load_image_pins(root)
    if not image_present(pins.local_image_ref):
        pytest.skip(f"image {pins.local_image_ref} is not present; build it first")
    model = load_schema_model_from_root(contracts_root_for(root))
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="dbt-roles", revision="head").ok
        _load_docs(store.url, [_document_row("doc-1")], "seed-roles")
        built = _run("build", "role-run", store.url)
        assert built.status == STATUS_OK
        engine = create_engine(store.url)
        try:
            with engine.begin() as connection:
                connection.execute(text(f"SET ROLE {ROLE_DBT}"))
                with pytest.raises(DBAPIError):
                    connection.execute(
                        text(
                            "INSERT INTO corpus.documents "
                            "(document_id, generation_id, contract_version) "
                            "VALUES ('doc-x', 'gen-1', '1.0.0')"
                        )
                    )
            with engine.begin() as connection:
                connection.execute(text(f"SET ROLE {ROLE_DBT}"))
                with pytest.raises(DBAPIError):
                    connection.execute(text("UPDATE alembic_version SET version_num = '0001'"))
            with engine.connect() as connection:
                findings = compare_live_catalog(connection, model)
            assert findings == []
        finally:
            engine.dispose()
        assert apply_revisions(root, url=store.url, run_id="dbt-roles-repeat", revision="head").ok

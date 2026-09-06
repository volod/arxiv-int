"""Offline coverage for staging COPY, upsert, and disposable helpers."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.disposable import _build_url, _published_port, image_present
from arxiv_int.stores.postgres.load import (
    copy_binary,
    load_canonical_batch,
    truncate_staging,
    upsert_rows,
)


def _root() -> Path:
    return discover_project_root(Path(__file__))


def _documents_table():
    return load_schema_model_from_root(contracts_root_for(_root())).metadata.tables[
        "corpus.documents"
    ]


def test_image_present_is_false_without_docker(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("arxiv_int.stores.postgres.disposable.shutil.which", lambda _name: None)
    assert image_present("arxiv-int/postgres:unused") is False


def test_image_present_uses_docker_inspect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.disposable.shutil.which", lambda _name: "/bin/docker"
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.disposable.subprocess.run",
        lambda *_a, **_k: SimpleNamespace(returncode=0),
    )
    assert image_present("arxiv-int/postgres:unused") is True


def test_published_port_parses_and_rejects_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.disposable.subprocess.run",
        lambda *_a, **_k: SimpleNamespace(returncode=0, stdout="0.0.0.0:54321\n", stderr=""),
    )
    assert _published_port("c1") == "54321"
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.disposable.subprocess.run",
        lambda *_a, **_k: SimpleNamespace(returncode=1, stdout="", stderr="gone"),
    )
    with pytest.raises(RuntimeError, match="gone"):
        _published_port("c1")
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.disposable.subprocess.run",
        lambda *_a, **_k: SimpleNamespace(returncode=0, stdout="127.0.0.1:\n", stderr=""),
    )
    with pytest.raises(RuntimeError, match="unparsed"):
        _published_port("c1")


def test_build_url_quotes_password() -> None:
    assert "p%40ss" in _build_url("user", "p@ss", "5432", "db")


def test_truncate_and_copy_and_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    table = _documents_table()
    connection = MagicMock()
    truncate_staging(connection, "documents")
    connection.execute.assert_called()
    connection.connection.dbapi_connection = None
    with pytest.raises(RuntimeError, match="closed"):
        copy_binary(connection, table, [{"document_id": "doc-1"}])
    raw = MagicMock()
    writer = MagicMock()
    copy_cm = MagicMock()
    copy_cm.__enter__.return_value = writer
    copy_cm.__exit__.return_value = False
    cursor = MagicMock()
    cursor.copy.return_value = copy_cm
    cursor_cm = MagicMock()
    cursor_cm.__enter__.return_value = cursor
    cursor_cm.__exit__.return_value = False
    raw.cursor.return_value = cursor_cm
    connection.connection.dbapi_connection = raw
    copy_binary(connection, table, [{"document_id": "doc-1"}])
    writer.write_row.assert_called()
    assert upsert_rows(connection, table, []) == 0
    assert upsert_rows(connection, table, [{"document_id": "doc-1", "generation_id": "g"}]) == 1


def test_load_canonical_batch_validates_then_copies(monkeypatch: pytest.MonkeyPatch) -> None:
    model = load_schema_model_from_root(contracts_root_for(_root()))
    monkeypatch.setattr("arxiv_int.stores.postgres.load.validate_rows", lambda *_a, **_k: None)
    monkeypatch.setattr("arxiv_int.stores.postgres.load.truncate_staging", lambda *_a, **_k: None)
    monkeypatch.setattr("arxiv_int.stores.postgres.load.copy_binary", lambda *_a, **_k: None)
    monkeypatch.setattr("arxiv_int.stores.postgres.load.upsert_rows", lambda *_a, **_k: 1)
    count = load_canonical_batch(
        MagicMock(),
        model,
        "documents",
        [{"document_id": "doc-1", "generation_id": "g", "contract_version": "1.0.0"}],
        project_root=_root(),
        run_id="unit-load",
    )
    assert count == 1

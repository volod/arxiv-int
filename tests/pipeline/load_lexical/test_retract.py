"""Snapshot retraction keeps loaded chunk ids and drops superseded ones."""

from unittest.mock import MagicMock, call

import pytest

from arxiv_int.pipeline.load_lexical import retract
from arxiv_int.pipeline.load_lexical.retract import keep_chunk_ids, retract_absent_chunks


def _sql(execute_call: call) -> str:
    statement = execute_call.args[0]
    return str(getattr(statement, "text", statement))


def _connection(deleted: int) -> MagicMock:
    connection = MagicMock()
    connection.execute.return_value.rowcount = deleted
    return connection


def _kept(connection: MagicMock) -> list[str]:
    return [
        row["chunk_id"]
        for item in connection.execute.call_args_list
        if "INSERT INTO" in _sql(item)
        for row in item.args[1]
    ]


def test_keep_chunk_ids_drop_blanks_and_duplicates() -> None:
    assert keep_chunk_ids(("keep-b", "", "keep-a", "keep-b")) == ("keep-b", "keep-a")
    assert keep_chunk_ids(()) == ()


def test_empty_snapshot_deletes_every_canonical_chunk() -> None:
    connection = _connection(4)
    assert retract_absent_chunks(connection, ()) == 4
    statements = [_sql(item) for item in connection.execute.call_args_list]
    assert statements == ["DELETE FROM corpus.chunks"]


def test_retract_deletes_only_ids_absent_from_the_loaded_snapshot() -> None:
    connection = _connection(2)
    assert retract_absent_chunks(connection, ("keep-1", "keep-1", "keep-2")) == 2
    statements = [_sql(item) for item in connection.execute.call_args_list]
    assert "CREATE TEMP TABLE load_lexical_keep_chunks" in statements[0]
    assert "ON COMMIT DROP" in statements[0]
    assert _kept(connection) == ["keep-1", "keep-2"]
    assert statements[-1].startswith("DELETE FROM corpus.chunks AS c WHERE NOT EXISTS")
    assert all("corpus.documents" not in item for item in statements)


def test_keep_set_spans_every_insert_batch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(retract, "_INSERT_BATCH", 2)
    loaded = tuple(f"keep-{index}" for index in range(5))
    connection = _connection(0)
    assert retract_absent_chunks(connection, loaded) == 0
    assert _kept(connection) == list(loaded)

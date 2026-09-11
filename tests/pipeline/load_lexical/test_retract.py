"""Snapshot retraction keeps loaded chunk ids and drops superseded ones."""

from unittest.mock import MagicMock, call

from arxiv_int.pipeline.load_lexical.retract import keep_chunk_ids, retract_absent_chunks


def _sql(execute_call: call) -> str:
    statement = execute_call.args[0]
    return str(getattr(statement, "text", statement))


def test_keep_chunk_ids_drop_blanks_and_duplicates() -> None:
    assert keep_chunk_ids(("keep-b", "", "keep-a", "keep-b")) == ("keep-b", "keep-a")
    assert keep_chunk_ids(()) == ()


def test_empty_snapshot_deletes_every_canonical_chunk() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = 4
    assert retract_absent_chunks(connection, ()) == 4
    statements = [_sql(item) for item in connection.execute.call_args_list]
    assert statements[0] == "SELECT count(*) FROM corpus.chunks"
    assert statements[1] == "DELETE FROM corpus.chunks"


def test_empty_store_does_not_issue_a_delete() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = 0
    assert retract_absent_chunks(connection, ()) == 0
    statements = [_sql(item) for item in connection.execute.call_args_list]
    assert statements == ["SELECT count(*) FROM corpus.chunks"]


def test_retract_deletes_ids_absent_from_the_loaded_snapshot() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = 2
    loaded = ("keep-1", "keep-1", "keep-2")
    assert retract_absent_chunks(connection, loaded) == 2
    statements = [_sql(item) for item in connection.execute.call_args_list]
    assert any("CREATE TEMP TABLE load_lexical_keep_chunks" in item for item in statements)
    inserted = next(
        item.args[1] for item in connection.execute.call_args_list if "INSERT INTO" in _sql(item)
    )
    assert inserted == [{"chunk_id": "keep-1"}, {"chunk_id": "keep-2"}]
    assert any("DELETE FROM corpus.chunks AS c" in item for item in statements)
    assert all("corpus.documents" not in item for item in statements)


def test_retract_skips_delete_when_the_store_already_matches() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = 0
    assert retract_absent_chunks(connection, ("keep-1",)) == 0
    statements = [_sql(item) for item in connection.execute.call_args_list]
    assert any("CREATE TEMP TABLE load_lexical_keep_chunks" in item for item in statements)
    assert not any("DELETE FROM corpus.chunks" in item for item in statements)

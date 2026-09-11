"""Retract canonical chunks that a complete snapshot no longer contains."""

import logging
from collections.abc import Sequence

from sqlalchemy import Connection, text

from arxiv_int.stores.projections.ids import require_ident

_LOG = logging.getLogger(__name__)
KEEP_TABLE = "load_lexical_keep_chunks"
_INSERT_BATCH = 2000
_KEEP_SQL = (
    f"CREATE TEMP TABLE {require_ident(KEEP_TABLE)} (chunk_id text PRIMARY KEY) ON COMMIT DROP"
)
_INSERT_SQL = f"INSERT INTO {require_ident(KEEP_TABLE)} (chunk_id) VALUES (:chunk_id)"
_ABSENT_COUNT_SQL = (
    "SELECT count(*) FROM corpus.chunks AS c WHERE NOT EXISTS ("
    f"SELECT 1 FROM {require_ident(KEEP_TABLE)} AS k WHERE k.chunk_id = c.chunk_id)"
)
_ABSENT_DELETE_SQL = (
    "DELETE FROM corpus.chunks AS c WHERE NOT EXISTS ("
    f"SELECT 1 FROM {require_ident(KEEP_TABLE)} AS k WHERE k.chunk_id = c.chunk_id)"
)


def keep_chunk_ids(loaded_ids: Sequence[str]) -> tuple[str, ...]:
    """Return distinct loaded chunk ids, preserving first-seen order."""
    return tuple(dict.fromkeys(item for item in loaded_ids if item))


def retract_absent_chunks(connection: Connection, loaded_ids: Sequence[str]) -> int:
    """Delete canonical chunks whose ids are not in this snapshot.

    The snapshot is the complete active chunk set for ``load-lexical``. Unchanged
    ids are kept by the preceding upsert. This delete stays in the same
    transaction so concurrent readers still see the previous generation until
    commit. An empty snapshot clears ``corpus.chunks``.
    """
    keep = keep_chunk_ids(loaded_ids)
    if not keep:
        count = _count(connection, "SELECT count(*) FROM corpus.chunks")
        if count:
            connection.execute(text("DELETE FROM corpus.chunks"))
        _LOG.info("load-lexical retracted empty_snapshot=true count=%d", count)
        return count
    connection.execute(text(_KEEP_SQL))
    for start in range(0, len(keep), _INSERT_BATCH):
        batch = keep[start : start + _INSERT_BATCH]
        connection.execute(text(_INSERT_SQL), [{"chunk_id": item} for item in batch])
    count = _count(connection, _ABSENT_COUNT_SQL)
    if count:
        connection.execute(text(_ABSENT_DELETE_SQL))
    _LOG.info("load-lexical retracted superseded_chunks=%d kept=%d", count, len(keep))
    return count


def _count(connection: Connection, statement: str) -> int:
    return int(connection.execute(text(statement)).scalar() or 0)

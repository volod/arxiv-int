"""Reconcile the canonical corpus against the built lexical projection."""

from dataclasses import dataclass

from sqlalchemy import Connection, text

from arxiv_int.stores.projections.ids import require_ident

FULL_SCOPE = "full"
PARTIAL_SCOPE = "partial"
_COUNT_SQL = "SELECT count(*) FROM {relation}"
_UNINDEXED_SQL = (
    "SELECT count(*) FROM corpus.chunks c "
    "LEFT JOIN {relation} p ON p.chunk_id = c.chunk_id WHERE p.chunk_id IS NULL"
)


@dataclass(frozen=True, slots=True)
class Reconciliation:
    """Counts and checksum agreement between the store and the projection."""

    canonical_documents: int
    canonical_chunks: int
    projection_rows: int
    unindexed_chunks: int
    checksum_scope: str
    checksum_match: bool
    retracted_chunks: int
    detail: str

    @property
    def ok(self) -> bool:
        """Return whether every required load reconciliation check passed.

        Every load retracts to its complete snapshot, so the canonical store must
        equal the loaded set: ``partial`` scope is drift, never a pass.
        """
        return (
            self.unindexed_chunks == 0
            and self.projection_rows == self.canonical_chunks
            and self.checksum_scope == FULL_SCOPE
            and self.checksum_match
        )

    def as_json_dict(self) -> dict[str, object]:
        """Return secret-free reconciliation evidence."""
        return {
            "canonicalChunks": self.canonical_chunks,
            "canonicalDocuments": self.canonical_documents,
            "checksumMatch": self.checksum_match,
            "checksumScope": self.checksum_scope,
            "detail": self.detail,
            "ok": self.ok,
            "projectionRows": self.projection_rows,
            "retractedChunks": self.retracted_chunks,
            "unindexedChunks": self.unindexed_chunks,
        }


def reconcile(
    connection: Connection,
    *,
    table: str,
    loaded_chunks: int,
    loaded_checksum: str,
    projection_checksum: str,
    retracted_chunks: int = 0,
) -> Reconciliation:
    """Compare canonical corpus counts with the covering table this run built."""
    relation = _qualified(table)
    documents = _count(connection, "corpus.documents")
    chunks = _count(connection, "corpus.chunks")
    projection_rows = _count(connection, relation)
    unindexed = int(
        connection.execute(text(_UNINDEXED_SQL.format(relation=relation))).scalar() or 0
    )
    scope = FULL_SCOPE if loaded_chunks == chunks else PARTIAL_SCOPE
    match = loaded_checksum == projection_checksum
    result = Reconciliation(
        canonical_documents=documents,
        canonical_chunks=chunks,
        projection_rows=projection_rows,
        unindexed_chunks=unindexed,
        checksum_scope=scope,
        checksum_match=match,
        retracted_chunks=retracted_chunks,
        detail=_detail(loaded_chunks, chunks, projection_rows, unindexed, match),
    )
    return result


def _detail(loaded: int, chunks: int, projection_rows: int, unindexed: int, match: bool) -> str:
    if unindexed:
        return f"{unindexed} canonical chunk(s) are missing from the lexical projection"
    if projection_rows != chunks:
        return f"projection holds {projection_rows} rows for {chunks} canonical chunks"
    if loaded != chunks:
        return f"canonical store holds {chunks} chunks but this snapshot loaded {loaded}"
    if not match:
        return "loaded chunk checksum does not match the projection checksum"
    return "canonical corpus and lexical projection reconcile"


def _count(connection: Connection, relation: str) -> int:
    return int(connection.execute(text(_COUNT_SQL.format(relation=relation))).scalar() or 0)


def _qualified(table: str) -> str:
    schema, _, name = table.partition(".")
    return f"{require_ident(schema)}.{require_ident(name)}"

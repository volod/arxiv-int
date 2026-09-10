"""Resolve lexical hits to canonical chunk source spans."""

from collections.abc import Sequence
from dataclasses import dataclass

from sqlalchemy import Connection, text

from arxiv_int.retrieval.metrics import SourceSpan

CITATION_SQL = (
    "SELECT chunk_id, document_id, start_char, end_char, chunker_id "
    "FROM corpus.chunks WHERE chunk_id = ANY(:chunk_ids) "
    "ORDER BY document_id, start_char, chunk_id"
)


@dataclass(frozen=True, slots=True)
class ChunkCitation:
    """One retrieved chunk bound to its original source character range."""

    chunk_id: str
    chunker_id: str
    span: SourceSpan

    def as_json_dict(self) -> dict[str, object]:
        """Return a secret-free citation row."""
        return {
            "chunkId": self.chunk_id,
            "chunkerId": self.chunker_id,
            "documentId": self.span.document_id,
            "endChar": self.span.end,
            "startChar": self.span.start,
        }


def resolve_citations(
    connection: Connection, chunk_ids: Sequence[str]
) -> tuple[ChunkCitation, ...]:
    """Map retrieved chunk ids onto the source spans canonical chunks retain."""
    if not chunk_ids:
        return ()
    rows = connection.execute(text(CITATION_SQL), {"chunk_ids": list(chunk_ids)}).fetchall()
    return tuple(
        ChunkCitation(
            chunk_id=str(row.chunk_id),
            chunker_id=str(row.chunker_id or ""),
            span=SourceSpan(
                document_id=str(row.document_id or ""),
                start=int(row.start_char or 0),
                end=int(row.end_char or 0),
            ),
        )
        for row in rows
    )


def unresolved_citations(
    chunk_ids: Sequence[str], citations: Sequence[ChunkCitation]
) -> tuple[str, ...]:
    """Return retrieved chunk ids that no canonical chunk row explains."""
    resolved = {item.chunk_id for item in citations}
    return tuple(sorted({value for value in chunk_ids if value not in resolved}))

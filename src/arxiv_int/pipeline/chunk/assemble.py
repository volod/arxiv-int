"""Pack classified blocks into bounded, sentence-aligned, source-aligned chunks."""

from dataclasses import replace

from arxiv_int.pipeline.chunk.blocks import HEADING, PROSE, TABLE, blocks, heading_text
from arxiv_int.pipeline.chunk.model import (
    TEXT_CHUNK,
    Block,
    Chunk,
    ChunkingError,
    ChunkPolicy,
    DocumentChunks,
)
from arxiv_int.pipeline.chunk.sentences import sentence_spans
from arxiv_int.pipeline.chunk.tables import table_chunks


class _Sections:
    """Track the current heading stack so every chunk carries its section path."""

    def __init__(self) -> None:
        self._levels: list[tuple[int, str]] = []

    def push(self, block: Block) -> None:
        """Enter one heading, dropping any deeper headings already open."""
        title = heading_text(block)
        if not title:
            return
        while self._levels and self._levels[-1][0] >= block.level:
            self._levels.pop()
        self._levels.append((block.level, title))

    def path(self) -> tuple[str, ...]:
        """Return the open heading titles from the outermost inward."""
        return tuple(title for _, title in self._levels)


def chunk_document(text: str, policy: ChunkPolicy) -> DocumentChunks:
    """Chunk one canonical document into structure-aware, offset-aligned units."""
    result = DocumentChunks()
    sections = _Sections()
    for block in blocks(text, policy):
        if len(result.chunks) >= policy.max_document_chunks:
            result.truncated = True
            break
        if block.kind == HEADING:
            sections.push(block)
            continue
        produced = (
            table_chunks(block, policy, len(result.chunks))
            if block.kind == TABLE
            else _prose_chunks(text, block, policy, len(result.chunks))
        )
        path = sections.path()
        result.chunks.extend(replace(chunk, section_path=path) for chunk in produced)
    if not result.chunks and text.strip():
        raise ChunkingError("no-chunks", "structure segmentation produced no chunks")
    return result


def _prose_chunks(text: str, block: Block, policy: ChunkPolicy, ordinal: int) -> list[Chunk]:
    if block.kind != PROSE:
        raise ChunkingError("unsupported-block", f"cannot chunk block kind {block.kind}")
    sentences = _bounded(text, sentence_spans(block.text, block.start), policy)
    chunks: list[Chunk] = []
    group: list[tuple[int, int]] = []
    for span in sentences:
        candidate = span[1] - group[0][0] if group else span[1] - span[0]
        if group and candidate > policy.target_chars:
            chunks.append(_chunk(text, ordinal + len(chunks), group))
            group = group[-policy.overlap_sentences :] if policy.overlap_sentences else []
            if group and span[1] - group[0][0] > policy.max_chars:
                group = []
        group.append(span)
    if group:
        chunks.append(_chunk(text, ordinal + len(chunks), group))
    return _merge_tail(text, chunks, policy)


def _bounded(text: str, spans: list[tuple[int, int]], policy: ChunkPolicy) -> list[tuple[int, int]]:
    bounded: list[tuple[int, int]] = []
    for start, end in spans:
        while end - start > policy.max_chars:
            split = _split_point(text, start, start + policy.max_chars)
            bounded.append((start, split))
            start = split
        if end > start:
            bounded.append((start, end))
    return bounded


def _split_point(text: str, start: int, limit: int) -> int:
    index = limit
    while index > start and not text[index - 1].isspace():
        index -= 1
    return index if index > start else limit


def _chunk(text: str, ordinal: int, group: list[tuple[int, int]]) -> Chunk:
    start, end = group[0][0], group[-1][1]
    body = text[start:end]
    trimmed = body.rstrip()
    return Chunk(
        ordinal,
        TEXT_CHUNK,
        trimmed,
        start,
        start + len(trimmed),
        sentences=len(group),
    )


def _merge_tail(text: str, chunks: list[Chunk], policy: ChunkPolicy) -> list[Chunk]:
    if len(chunks) < 2:
        return chunks
    last, previous = chunks[-1], chunks[-2]
    if len(last.text) >= policy.min_chars:
        return chunks
    if last.end - previous.start > policy.max_chars:
        return chunks
    merged = text[previous.start : last.end].rstrip()
    chunks[-2] = Chunk(
        previous.ordinal,
        TEXT_CHUNK,
        merged,
        previous.start,
        previous.start + len(merged),
        sentences=previous.sentences + last.sentences,
    )
    return chunks[:-1]

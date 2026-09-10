"""Row-group chunking that repeats the detected header in every table chunk."""

from arxiv_int.pipeline.chunk.blocks import is_separator
from arxiv_int.pipeline.chunk.model import TABLE_CHUNK, Block, Chunk, ChunkPolicy


def table_chunks(block: Block, policy: ChunkPolicy, ordinal: int) -> list[Chunk]:
    """Split one table block into row groups that each carry the header rows."""
    rows = _rows(block)
    header_rows, body_rows = _split_header(rows)
    if not body_rows:
        return [
            Chunk(
                ordinal,
                TABLE_CHUNK,
                block.text,
                block.start,
                block.end,
                sentences=len(rows),
            )
        ]
    prefix = "\n".join(text for _, _, text in header_rows)
    prefix_span = (header_rows[0][0], header_rows[-1][1]) if header_rows else None
    budget = max(policy.target_chars - len(prefix), policy.min_chars)
    chunks: list[Chunk] = []
    group: list[tuple[int, int, str]] = []
    size = 0
    for row in body_rows:
        if group and size + len(row[2]) + 1 > budget:
            chunks.append(_chunk(ordinal + len(chunks), prefix, prefix_span, group))
            group = []
            size = 0
        group.append(row)
        size += len(row[2]) + 1
    if group:
        chunks.append(_chunk(ordinal + len(chunks), prefix, prefix_span, group))
    return chunks


def _rows(block: Block) -> list[tuple[int, int, str]]:
    rows: list[tuple[int, int, str]] = []
    position = block.start
    for line in block.text.split("\n"):
        end = position + len(line)
        if line.strip():
            rows.append((position, end, line))
        position = end + 1
    return rows


def _split_header(
    rows: list[tuple[int, int, str]],
) -> tuple[list[tuple[int, int, str]], list[tuple[int, int, str]]]:
    for index, row in enumerate(rows):
        if is_separator(row[2]):
            return rows[:index], rows[index + 1 :]
    if len(rows) < 2:
        return [], rows
    return rows[:1], rows[1:]


def _chunk(
    ordinal: int,
    prefix: str,
    prefix_span: tuple[int, int] | None,
    group: list[tuple[int, int, str]],
) -> Chunk:
    body = "\n".join(text for _, _, text in group)
    text = f"{prefix}\n{body}" if prefix else body
    return Chunk(
        ordinal,
        TABLE_CHUNK,
        text,
        group[0][0],
        group[-1][1],
        prefix_chars=len(prefix) + 1 if prefix else 0,
        prefix_span=prefix_span,
        sentences=len(group),
    )

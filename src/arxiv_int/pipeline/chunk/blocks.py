"""Segment canonical text into headings, tables, and prose blocks."""

import re

from arxiv_int.pipeline.chunk.model import Block, ChunkPolicy

HEADING = "heading"
TABLE = "table"
PROSE = "prose"

_NUMBERED = re.compile(r"^\d+(?:\.\d+)*[.)]?\s+\S")
_MARKDOWN = re.compile(r"^(#{1,6})\s+\S")
_SEPARATOR = re.compile(r"^[\s|:+-]+$")
_SENTENCE_END = frozenset(".!?:;,\u2026")
_CELL_SEPARATORS = ("|", "\t")


def blocks(text: str, policy: ChunkPolicy) -> list[Block]:
    """Return the ordered blocks of one canonical document."""
    result: list[Block] = []
    for start, end in _paragraphs(text):
        result.extend(_classify(text, start, end, policy))
    return result


def _paragraphs(text: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    start: int | None = None
    for line_start, line_end in _lines(text):
        if text[line_start:line_end].strip():
            start = line_start if start is None else start
            continue
        if start is not None:
            spans.append((start, line_start))
            start = None
    if start is not None:
        spans.append((start, len(text)))
    return [(begin, _trim(text, begin, finish)) for begin, finish in spans]


def _lines(text: str) -> list[tuple[int, int]]:
    rows: list[tuple[int, int]] = []
    position = 0
    for line in text.split("\n"):
        rows.append((position, position + len(line)))
        position += len(line) + 1
    return rows


def _trim(text: str, start: int, end: int) -> int:
    while end > start and text[end - 1].isspace():
        end -= 1
    return end


def _classify(text: str, start: int, end: int, policy: ChunkPolicy) -> list[Block]:
    body = text[start:end]
    rows = [row for row in body.split("\n") if row.strip()]
    if _is_table(rows, policy):
        return [Block(TABLE, start, end, body)]
    heading = _heading(rows[0], policy) if rows else None
    if heading is not None and len(rows) == 1:
        return [Block(HEADING, start, end, body, heading)]
    if heading is not None:
        split = start + body.index("\n")
        return [
            Block(HEADING, start, split, text[start:split], heading),
            Block(PROSE, split + 1, end, text[split + 1 : end]),
        ]
    return [Block(PROSE, start, end, body)]


def _is_table(rows: list[str], policy: ChunkPolicy) -> bool:
    if len(rows) < policy.table_min_rows:
        return False
    marked = sum(1 for row in rows if any(mark in row for mark in _CELL_SEPARATORS))
    return marked >= max(policy.table_min_rows, (len(rows) + 1) // 2)


def _heading(row: str, policy: ChunkPolicy) -> int | None:
    stripped = row.strip()
    if not stripped or len(stripped) > policy.heading_max_chars:
        return None
    markdown = _MARKDOWN.match(stripped)
    if markdown is not None:
        return len(markdown.group(1))
    if stripped[-1] in _SENTENCE_END:
        return None
    numbered = _NUMBERED.match(stripped)
    if numbered is not None:
        return stripped.split(None, 1)[0].rstrip(".)").count(".") + 1
    if stripped == stripped.upper() and any(char.isalpha() for char in stripped):
        return 1
    return None


def is_separator(row: str) -> bool:
    """Report whether one table row only draws a rule between header and body."""
    return bool(row.strip()) and _SEPARATOR.match(row.strip()) is not None


def heading_text(block: Block) -> str:
    """Return the display text of one heading block without markup."""
    return block.text.strip().lstrip("#").strip()

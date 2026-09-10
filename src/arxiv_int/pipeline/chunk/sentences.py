"""Deterministic, script-neutral sentence segmentation over canonical text."""

_TERMINATORS = frozenset(".!?\u2026")
_CLOSERS = frozenset("\"')]}\u00bb\u201d\u2019")
_OPENERS = frozenset("\"'([{\u00ab\u201c\u2018")
_MIN_ABBREVIATION_LETTERS = 2


def sentence_spans(text: str, start: int) -> list[tuple[int, int]]:
    """Split one block into absolute sentence spans without dropping characters.

    A terminator ends a sentence only when the following visible character starts a
    new one, which keeps initials and lowercase abbreviations inside one sentence
    regardless of the document's script.
    """
    spans: list[tuple[int, int]] = []
    opened = 0
    total = len(text)
    index = 0
    while index < total:
        if text[index] not in _TERMINATORS:
            index += 1
            continue
        end, gap = _after_terminator(text, index, total)
        if _breaks(text, index, end, gap, total):
            spans.append((start + opened, start + gap))
            opened = gap
        index = max(end, index + 1)
    if opened < total:
        spans.append((start + opened, start + total))
    return spans


def _after_terminator(text: str, index: int, total: int) -> tuple[int, int]:
    end = index + 1
    while end < total and text[end] in _TERMINATORS:
        end += 1
    while end < total and text[end] in _CLOSERS:
        end += 1
    gap = end
    while gap < total and text[gap].isspace():
        gap += 1
    return end, gap


def _breaks(text: str, terminator: int, end: int, gap: int, total: int) -> bool:
    if gap == end and gap < total:
        return False
    if gap >= total:
        return False
    if not _starts_sentence(text[gap]):
        return False
    return _preceding_word_length(text, terminator) >= _MIN_ABBREVIATION_LETTERS


def _starts_sentence(char: str) -> bool:
    return char.isupper() or char.isdigit() or char in _OPENERS


def _preceding_word_length(text: str, terminator: int) -> int:
    index = terminator
    length = 0
    while index > 0 and (text[index - 1].isalpha() or text[index - 1].isdigit()):
        index -= 1
        length += 1
    return length

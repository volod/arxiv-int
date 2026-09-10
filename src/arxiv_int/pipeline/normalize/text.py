"""Offset-preserving Unicode normalization and search-view derivation."""

import unicodedata
from bisect import bisect_right
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

ALGORITHM_VERSION = "1"
_LINE_SEPARATORS = frozenset("\x0b\x0c\x1c\x1d\x1e\x85\u2028\u2029")
_KEPT_CONTROLS = frozenset("\t\n")
_COMBINING = frozenset({"Mn", "Mc", "Me"})
_YO = {"\u0451": "\u0435", "\u0401": "\u0415"}


@dataclass(frozen=True, slots=True)
class OffsetRun:
    """One contiguous source region and the target region it produced."""

    source_start: int
    source_end: int
    target_start: int
    target_end: int

    @property
    def aligned(self) -> bool:
        """Report whether offsets inside this run map one to one."""
        return self.source_end - self.source_start == self.target_end - self.target_start


class OffsetMap:
    """Reversible character-offset mapping between two views of one document."""

    def __init__(self, runs: tuple[OffsetRun, ...]) -> None:
        self.runs = runs
        self._by_source = [run.source_start for run in runs]
        self._by_target = [run.target_start for run in runs]

    def to_target(self, index: int) -> int:
        """Map one source offset onto the closest surviving target offset."""
        position = bisect_right(self._by_source, index) - 1
        if position < 0:
            return 0
        run = self.runs[position]
        if index >= run.source_end:
            return run.target_end
        if run.aligned:
            return run.target_start + (index - run.source_start)
        return run.target_start

    def to_source(self, index: int) -> int:
        """Map one target offset back onto the original source offset."""
        position = bisect_right(self._by_target, index) - 1
        if position < 0:
            return self.runs[0].source_start if self.runs else 0
        run = self.runs[position]
        if index >= run.target_end:
            return run.source_end
        if run.aligned:
            return run.source_start + (index - run.target_start)
        return run.source_start

    def serialize(self) -> list[list[int]]:
        """Return the compact reviewable form retained beside each document."""
        return [
            [run.source_start, run.source_end, run.target_start, run.target_end]
            for run in self.runs
        ]


@dataclass(frozen=True, slots=True)
class TextView:
    """One derived text view and its mapping back to the view it came from."""

    text: str
    offsets: OffsetMap


def load_offset_map(runs: Iterable[Sequence[int]]) -> OffsetMap:
    """Rebuild one offset map from its retained compact form."""
    return OffsetMap(
        tuple(OffsetRun(int(run[0]), int(run[1]), int(run[2]), int(run[3])) for run in runs)
    )


class _Builder:
    """Accumulate emitted pieces and merge adjacent one-to-one runs."""

    def __init__(self) -> None:
        self.pieces: list[str] = []
        self.runs: list[OffsetRun] = []
        self.length = 0

    def emit(self, source_start: int, source_end: int, piece: str) -> None:
        """Record one source region and the text it contributed."""
        if not piece:
            return
        run = OffsetRun(source_start, source_end, self.length, self.length + len(piece))
        if self.runs:
            previous = self.runs[-1]
            if (
                previous.aligned
                and run.aligned
                and previous.source_end == run.source_start
                and previous.target_end == run.target_start
            ):
                self.runs[-1] = OffsetRun(
                    previous.source_start, run.source_end, previous.target_start, run.target_end
                )
                self.pieces.append(piece)
                self.length += len(piece)
                return
        self.runs.append(run)
        self.pieces.append(piece)
        self.length += len(piece)

    def view(self) -> TextView:
        """Seal the accumulated pieces into one immutable view."""
        return TextView("".join(self.pieces), OffsetMap(tuple(self.runs)))


def canonical_view(text: str) -> TextView:
    """Build the NFC canonical view that preserves original character offsets."""
    builder = _Builder()
    index = 0
    total = len(text)
    while index < total:
        index = _emit_canonical(builder, text, index, total)
    return builder.view()


def _emit_canonical(builder: _Builder, text: str, index: int, total: int) -> int:
    char = text[index]
    if char == "\r":
        width = 2 if text.startswith("\r\n", index) else 1
        builder.emit(index, index + width, "\n")
        return index + width
    if char in _LINE_SEPARATORS:
        builder.emit(index, index + 1, "\n")
        return index + 1
    category = unicodedata.category(char)
    if category == "Zs":
        builder.emit(index, index + 1, " ")
        return index + 1
    if category in {"Cc", "Cf", "Cs", "Co", "Cn"} and char not in _KEPT_CONTROLS:
        return index + 1
    end = index + 1
    while end < total and unicodedata.category(text[end]) in _COMBINING:
        end += 1
    builder.emit(index, end, unicodedata.normalize("NFC", text[index:end]))
    return end


def search_view(canonical: str) -> TextView:
    """Build the casefolded, whitespace-collapsed view used for search and shingles."""
    builder = _Builder()
    index = 0
    total = len(canonical)
    while index < total:
        char = canonical[index]
        if char.isspace():
            end = index
            while end < total and canonical[end].isspace():
                end += 1
            interior = bool(builder.length) and end < total
            builder.emit(index, end, " " if interior else "")
            index = end
            continue
        builder.emit(index, index + 1, _YO.get(char, char).casefold())
        index += 1
    return builder.view()

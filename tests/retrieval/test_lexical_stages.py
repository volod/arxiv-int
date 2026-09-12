"""A refused query stage must not hide a later stage, or its own error."""

from dataclasses import dataclass
from typing import Any

import pytest
from sqlalchemy.exc import ProgrammingError

from arxiv_int.retrieval.lexical import search
from arxiv_int.retrieval.lexical_model import LexicalRequest
from arxiv_int.retrieval.projection import LexicalQueryError, LexicalTarget
from arxiv_int.retrieval.query_normalization import query_plan

TYPED = "gjcnfdrf["
INTENDED = "поставках"
TARGET = LexicalTarget("lexical-run1", "run1", "search.t", "t_bm25", 1, "sum", "active")


@dataclass(frozen=True)
class _Hit:
    chunk_id: str = "chunk-1"
    document_id: str = "doc-1"
    title: str = "title"
    language: str = "rus"
    score: float = 1.5
    snippet: str = "snippet"


class _Result:
    def __init__(self, rows: list[_Hit]) -> None:
        self._rows = rows

    def fetchall(self) -> list[_Hit]:
        return self._rows

    def scalar(self) -> int:
        return len(self._rows)


class _Connection:
    """Refuse the literal query the way the engine does and match only the intended text."""

    def __init__(self, matching: str | None) -> None:
        self.matching = matching
        self.stages: list[tuple[str, ...]] = []

    def execute(self, statement: Any, parameters: Any = None) -> _Result:
        texts = tuple(
            str(value)
            for key, value in sorted((parameters or {}).items())
            if key.startswith(("query_text_", "fuzzy_text_"))
        )
        self.stages.append(texts)
        if TYPED in texts:
            raise ProgrammingError("stmt", {}, Exception("syntax error at '['"))
        matched = self.matching is not None and self.matching in texts
        return _Result([_Hit()] if matched else [])


def test_a_refused_literal_stage_falls_through_to_the_layout_reading() -> None:
    connection = _Connection(INTENDED)

    result = search(connection, LexicalRequest(query=TYPED), target=TARGET)

    assert INTENDED in query_plan(TYPED).fallback
    assert result.query_stage == "fallback"
    assert result.total == 1 and result.hits[0].chunk_id == "chunk-1"
    assert connection.stages[0] == (TYPED,)


def test_an_unparseable_query_that_nothing_rescues_still_reports_its_error() -> None:
    connection = _Connection(None)

    with pytest.raises(LexicalQueryError, match="syntax error"):
        search(connection, LexicalRequest(query=TYPED), target=TARGET)

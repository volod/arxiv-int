"""The active lexical target must be verified against the profile that built it."""

from dataclasses import dataclass
from typing import Any

import pytest

from arxiv_int.retrieval.projection import LexicalUnavailableError, active_target
from arxiv_int.stores.projections.adapters.lexical import TOKENIZER_FINGERPRINT
from arxiv_int.stores.projections.model import KIND_LEXICAL, STATUS_ACTIVE
from arxiv_int.stores.projections.profiles import engine_profile, projection_input_fingerprint


@dataclass(frozen=True)
class _Row:
    projection_id: str
    version_id: str
    status: str
    row_count: int
    checksum: str
    input_fingerprint: str


class _Connection:
    """Return one registry row for the single select ``active_target`` issues."""

    def __init__(self, row: _Row | None) -> None:
        self.row = row

    def execute(self, statement: Any) -> "_Connection":
        return self

    def first(self) -> _Row | None:
        return self.row


def _row(**overrides: Any) -> _Row:
    values: dict[str, Any] = {
        "projection_id": "lexical-run1",
        "version_id": "run1",
        "status": STATUS_ACTIVE,
        "row_count": 7,
        "checksum": "sum",
        "input_fingerprint": projection_input_fingerprint(KIND_LEXICAL, "run1", "sum"),
    }
    values.update(overrides)
    return _Row(**values)


def test_input_fingerprint_binds_the_engine_profile() -> None:
    bound = projection_input_fingerprint(KIND_LEXICAL, "run1", "sum")

    assert engine_profile(KIND_LEXICAL) == TOKENIZER_FINGERPRINT
    assert bound != projection_input_fingerprint(KIND_LEXICAL, "run1", "other")
    with pytest.raises(ValueError, match="unknown projection kind"):
        engine_profile("bm25")


def test_matching_profile_resolves_the_active_target() -> None:
    target = active_target(_Connection(_row()))

    assert target.version_id == "run1"
    assert target.tokenizer_fingerprint == TOKENIZER_FINGERPRINT


def test_a_projection_built_under_another_profile_is_refused() -> None:
    stale = _row(input_fingerprint="0" * 64)

    with pytest.raises(LexicalUnavailableError, match="tokenizer profile"):
        active_target(_Connection(stale))

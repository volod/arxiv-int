"""Taxonomy code shape, depth, parent and kind."""

import pytest

from arxiv_int.classification.vocabulary.codes import (
    KIND_DOMAIN,
    KIND_FIELD,
    KIND_SUBFIELD,
    CodeError,
    code_depth,
    kind_for,
    parent_code,
    require_code,
)


def test_code_carries_depth_parent_and_kind() -> None:
    assert (code_depth("04"), parent_code("04"), kind_for("04")) == (1, None, KIND_DOMAIN)
    assert (code_depth("04.02"), parent_code("04.02"), kind_for("04.02")) == (2, "04", KIND_FIELD)
    assert parent_code("04.02.01") == "04.02"
    assert kind_for("04.02.01") == KIND_SUBFIELD


@pytest.mark.parametrize("text", ["", "4", "04.2", "04..02", "04.02.", "a4", " 04", "04-02"])
def test_malformed_codes_are_refused(text: str) -> None:
    with pytest.raises(CodeError):
        require_code(text)


def test_codes_deeper_than_a_subfield_have_no_kind() -> None:
    assert code_depth("04.02.01.03") == 4
    with pytest.raises(CodeError):
        kind_for("04.02.01.03")

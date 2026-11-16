"""Reversible path-safe class tokens and ASCII slugs."""

import re

import pytest

from arxiv_int.classification.vocabulary.tokens import (
    TokenError,
    ascii_slug,
    class_id_from_token,
    class_token,
)

CLASS_IDS = [
    "tax:04",
    "tax:04.02",
    "tax:04.02.01",
    "ext:supplier-letters",
    "ext:a_b",
    "ext:A/Z.",
    "unclassified",
    "unreadable",
]


@pytest.mark.parametrize("class_id", CLASS_IDS)
def test_token_round_trips_and_is_one_safe_component(class_id: str) -> None:
    token = class_token(class_id)
    assert class_id_from_token(token) == class_id
    assert re.fullmatch(r"[0-9a-z._-]+", token)
    assert not token.startswith(".")
    assert not token.endswith(".")


def test_namespace_prefixes_keep_tokens_disjoint() -> None:
    tokens = [class_token(class_id) for class_id in [*CLASS_IDS, "ext:t04", "tax:99"]]
    assert len(set(tokens)) == len(tokens)
    assert class_token("tax:04.02.01") == "t04.02.01"
    assert class_token("unclassified") == "_unclassified"


@pytest.mark.parametrize("token", ["t_zz", "t_2F", "tA", "q5", "_bogus", "t", "t_30"])
def test_malformed_or_non_canonical_tokens_are_refused(token: str) -> None:
    with pytest.raises(TokenError):
        class_id_from_token(token)


def test_slug_is_ascii_and_cut_at_a_word_boundary() -> None:
    slug = ascii_slug("Environmental science. Conservation of natural resources", 40)
    assert slug == "environmental-science-conservation-of"
    assert ascii_slug("Caf\u00e9 & Bar", 40) == "cafe-bar"
    assert (
        ascii_slug(
            "\u0421\u0442\u0440\u043e\u0438\u0442\u0435\u043b\u044c\u0441\u0442\u0432\u043e", 40
        )
        == ""
    )

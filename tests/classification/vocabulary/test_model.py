"""Parent closure, children, and nearest-ancestor resolution over taxonomy codes."""

import pytest

from arxiv_int.classification.vocabulary.codes import kind_for, parent_code
from arxiv_int.classification.vocabulary.model import (
    Resolution,
    Scheme,
    SchemeClass,
    SchemeCycleError,
)
from arxiv_int.classification.vocabulary.outcomes import taxonomy_class_id

CAPTIONS = (("en", "Fixture"), ("ru", "\u0420\u0423"), ("uk", "\u0423\u041a"))


def tax(code: str) -> SchemeClass:
    parent = parent_code(code)
    return SchemeClass(
        taxonomy_class_id(code),
        "tax",
        code,
        taxonomy_class_id(parent) if parent else None,
        kind_for(code),
        CAPTIONS,
    )


SCHEME = Scheme.of([tax("04"), tax("04.02"), tax("04.02.01"), tax("04.03"), tax("05")])


def test_path_depth_and_children_follow_parents() -> None:
    assert SCHEME.path("tax:04.02.01") == ("tax:04", "tax:04.02", "tax:04.02.01")
    assert SCHEME.depth("tax:04.03") == 2
    assert SCHEME.children("tax:04") == ("tax:04.02", "tax:04.03")
    assert SCHEME.children(None) == ("tax:04", "tax:05")


def test_deep_code_resolves_to_the_nearest_present_class() -> None:
    assert SCHEME.resolve_code("04.02.01") == Resolution("tax:04.02.01", "04.02.01", False)
    assert SCHEME.resolve_code("04.02.01.07") == Resolution("tax:04.02.01", "04.02.01.07", True)
    assert SCHEME.resolve_code("04.09") == Resolution("tax:04", "04.09", True)


def test_absent_domain_or_malformed_code_does_not_resolve() -> None:
    assert SCHEME.resolve_code("07.01") is None
    assert SCHEME.resolve_code("4.2") is None


def test_parent_loop_is_refused() -> None:
    first = SchemeClass("ext:a", "ext", None, "ext:b", "extension", CAPTIONS)
    second = SchemeClass("ext:b", "ext", None, "ext:a", "extension", CAPTIONS)
    with pytest.raises(SchemeCycleError):
        Scheme.of([first, second]).ancestors("ext:a")

"""Structural validation: duplicates, orphans, cycles, namespaces, codes, captions, tokens."""

from dataclasses import replace

from arxiv_int.classification.vocabulary.build import project_classes
from arxiv_int.classification.vocabulary.model import SchemeClass
from arxiv_int.classification.vocabulary.policy import Licence, SchemePolicy, load_scheme_policy
from arxiv_int.classification.vocabulary.validate import (
    errors,
    validate_classes,
    validate_licence,
)
from tests.classification.vocabulary.test_model import CAPTIONS, tax

POLICY = load_scheme_policy()


def base() -> list[SchemeClass]:
    return [tax("04"), tax("04.02"), tax("04.02.01"), *project_classes(POLICY)]


def codes(classes: list[SchemeClass], policy: SchemePolicy = POLICY) -> set[str]:
    return {item.code for item in errors(validate_classes(classes, policy))}


def ext(name: str, parent: str | None = "tax:04") -> SchemeClass:
    return SchemeClass(name, "ext", None, parent, "extension", CAPTIONS)


def test_valid_classes_have_no_errors() -> None:
    assert codes(base()) == set()
    assert codes([*base(), ext("ext:supplier-letters", "tax:04.02.01")]) == set()


def test_duplicate_orphan_and_cycle_fail() -> None:
    assert "duplicate-class" in codes([*base(), tax("04.02")])
    assert "orphan-parent" in codes([*base(), tax("05.01")])
    assert "cycle" in codes([*base(), ext("ext:aa", "ext:bb"), ext("ext:bb", "ext:aa")])


def test_namespace_collisions_fail() -> None:
    assert "namespace-collision" in codes([*base(), ext("ext:unclassified")])
    assert "extension-name" in codes([*base(), ext("ext:0402")])
    assert "namespace-collision" in codes([*base(), ext("letters")])
    assert "orphan-parent" in codes([*base(), ext("ext:letters", "unclassified")])
    mislabelled = SchemeClass("tax:04.03", "ext", None, "tax:04", "extension", CAPTIONS)
    assert "namespace-collision" in codes([*base(), mislabelled])


def test_codes_must_agree_with_id_kind_and_parent() -> None:
    wrong_code = replace(tax("04.03"), code="04.04")
    wrong_parent = replace(tax("04.03"), parent_id="tax:04.02")
    wrong_kind = replace(tax("04.03"), kind="subfield")
    malformed = SchemeClass("tax:4", "tax", "4", None, "domain", CAPTIONS)
    assert "code-mismatch" in codes([*base(), wrong_code])
    assert "code-mismatch" in codes([*base(), wrong_parent])
    assert "invalid-code" in codes([*base(), wrong_kind])
    assert "invalid-code" in codes([*base(), malformed])


def test_every_required_caption_language_is_needed() -> None:
    no_uk = replace(tax("04.03"), captions=(("en", "Fixture"), ("ru", "\u0420\u0423")))
    assert codes([*base(), no_uk]) == {"missing-caption"}


def test_overlong_token_fails() -> None:
    assert "token-overlong" in codes(base(), replace(POLICY, max_token_bytes=3))


def test_licence_needs_name_and_url() -> None:
    assert validate_licence("taxonomy", Licence("MIT", "https://opensource.org/license/mit")) == []
    assert [item.code for item in validate_licence("taxonomy", Licence("", ""))] == [
        "missing-licence"
    ]

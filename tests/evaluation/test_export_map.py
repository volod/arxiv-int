import pytest

from arxiv_int.evaluation.export_catalog import parse_identity_catalog
from arxiv_int.evaluation.export_errors import ExportCollisionError, ExportSpanError
from arxiv_int.evaluation.export_map import _claim, build_substitution_table
from tests.evaluation.export_support import excerpt_text, identities_payload


def test_aliases_and_shared_contacts_share_substitutes() -> None:
    catalog = parse_identity_catalog(identities_payload())
    table = build_substitution_table(catalog, {"excerpt.txt": excerpt_text()})
    alpha = table.entity_labels["person:alpha"]
    assert table.reference_map["aliases"]["A. Example"] == alpha
    email = "alice.example@acme.example"
    assert email in table.structured
    assert table.structured[email] == table.structured[email.lower()]


def test_same_name_entities_are_ambiguous_without_spans() -> None:
    catalog = parse_identity_catalog(identities_payload())
    table = build_substitution_table(catalog, {"excerpt.txt": excerpt_text()})
    assert "Alice Example" in table.ambiguous
    assert table.entity_labels["person:alpha"] != table.entity_labels["person:beta"]


def test_stale_span_text_is_refused() -> None:
    payload = identities_payload()
    payload["spans"] = [
        {"artifact": "excerpt.txt", "end": 4, "entity_id": "person:alpha", "start": 0}
    ]
    catalog = parse_identity_catalog(payload)
    with pytest.raises(ExportSpanError, match="does not match"):
        build_substitution_table(catalog, {"excerpt.txt": excerpt_text()})


def test_substitution_collision_is_refused() -> None:
    claims = {"same": "entity:a"}
    with pytest.raises(ExportCollisionError, match="collided"):
        _claim(claims, "entity:b", "same")
    assert _claim(claims, "entity:a", "same") == "same"

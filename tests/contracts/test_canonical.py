"""Canonical semantic model loading tests."""

import pytest

from arxiv_int.contracts.canonical import load_canonical_model
from tests.contracts._fixtures import write_contract_tree


def test_loads_required_bindings_and_terms(tmp_path) -> None:
    write_contract_tree(tmp_path)

    model = load_canonical_model(tmp_path / "canonical")

    assert model.model_ref == "urn:arxiv-int:model:1.0.0"
    assert model.entities() == ("document",)
    assert model.required_bindings("document") == frozenset({"document.documentId"})
    assert model.has_term("urn:arxiv-int:document-id")


def test_unknown_entity_is_empty(tmp_path) -> None:
    write_contract_tree(tmp_path)
    model = load_canonical_model(tmp_path / "canonical")

    assert model.fields_for("missing") == ()
    assert model.required_bindings("missing") == frozenset()


def test_model_vocabulary_is_immutable(tmp_path) -> None:
    write_contract_tree(tmp_path)
    model = load_canonical_model(tmp_path / "canonical")

    with pytest.raises(TypeError):
        model.semantic_terms["new"] = model.semantic_terms["urn:arxiv-int:document-id"]  # type: ignore[index]

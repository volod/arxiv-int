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


def test_rejects_parent_reference_escape(tmp_path) -> None:
    write_contract_tree(tmp_path)
    model = tmp_path / "canonical" / "model.yaml"
    model.write_text(
        model.read_text(encoding="utf-8").replace(
            "odcs/document.odcs.yaml", "../datasets/documents.odcs.yaml"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="escapes contract root"):
        load_canonical_model(tmp_path / "canonical")


def test_rejects_absolute_reference_escape(tmp_path) -> None:
    write_contract_tree(tmp_path)
    absolute = tmp_path / "datasets" / "documents.odcs.yaml"
    model = tmp_path / "canonical" / "model.yaml"
    model.write_text(
        model.read_text(encoding="utf-8").replace("odcs/document.odcs.yaml", str(absolute)),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="must be relative"):
        load_canonical_model(tmp_path / "canonical")


def test_rejects_symlink_escape(tmp_path) -> None:
    write_contract_tree(tmp_path)
    outside = tmp_path / "outside.odcs.yaml"
    outside.write_text("schema: []\n", encoding="utf-8")
    link = tmp_path / "canonical" / "odcs" / "escape.odcs.yaml"
    link.symlink_to(outside)
    model = tmp_path / "canonical" / "model.yaml"
    model.write_text(
        model.read_text(encoding="utf-8").replace(
            "odcs/document.odcs.yaml", "odcs/escape.odcs.yaml"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="escapes contract root"):
        load_canonical_model(tmp_path / "canonical")


def test_rejects_duplicate_and_malformed_bindings(tmp_path) -> None:
    write_contract_tree(tmp_path)
    odcs = tmp_path / "canonical" / "odcs" / "document.odcs.yaml"
    odcs.write_text(
        "schema:\n"
        "  - properties:\n"
        "      - name: document_id\n"
        "        required: true\n"
        "        customProperties:\n"
        "          - property: canonicalBinding\n"
        "            value:\n"
        "              binding: document.documentId\n"
        "              semanticTerm: urn:arxiv-int:document-id\n"
        "              reviewerNote: keep-me\n"
        "      - name: alt_id\n"
        "        customProperties:\n"
        "          - property: canonicalBinding\n"
        "            value:\n"
        "              binding: document.documentId\n"
        "              semanticTerm: urn:arxiv-int:document-id\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="ambiguous binding"):
        load_canonical_model(tmp_path / "canonical")

    odcs.write_text(
        "schema:\n"
        "  - properties:\n"
        "      - name: document_id\n"
        "        customProperties:\n"
        "          - property: canonicalBinding\n"
        "            value:\n"
        "              binding: document.documentId\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing required keys"):
        load_canonical_model(tmp_path / "canonical")

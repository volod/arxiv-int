"""Portable registry and generator-dispatch tests."""

import json

import pytest

from arxiv_int.contracts.catalog.fingerprint import semantic_metadata_hash
from arxiv_int.contracts.catalog.registry import FileRegistry, MetadataDriftError
from arxiv_int.contracts.generate import generate_registered
from tests.contracts.catalog._fixtures import write_contract_tree


class JsonGenerator:
    """Deterministic fixture generator implementing the public protocol."""

    def generate(self, odcs_document, contract_id):
        return json.dumps(
            {"contract": contract_id, "version": odcs_document["version"]},
            sort_keys=True,
        )


def test_registry_loads_and_generates_without_sibling_checkout(tmp_path) -> None:
    write_contract_tree(tmp_path)
    registry = FileRegistry(tmp_path)

    output = generate_registered(
        registry, "documents", JsonGenerator(), tmp_path / "generated" / "documents.json"
    )

    assert registry.contract_ids() == ("documents",)
    assert output.read_text(encoding="utf-8") == ('{"contract": "documents", "version": "1.0.0"}')


def test_registry_verifies_reviewed_semantic_fingerprint(tmp_path) -> None:
    write_contract_tree(tmp_path)
    expected = semantic_metadata_hash(FileRegistry(tmp_path).load_mapping("documents"))
    write_contract_tree(tmp_path, expected)

    assert FileRegistry(tmp_path).verify_semantic_fingerprint("documents") == expected


def test_registry_rejects_semantic_drift(tmp_path) -> None:
    write_contract_tree(tmp_path, "deadbeef")

    with pytest.raises(MetadataDriftError, match="semanticMetadataHash changed"):
        FileRegistry(tmp_path).verify_semantic_fingerprint("documents")


def test_registry_rejects_reference_outside_root(tmp_path) -> None:
    write_contract_tree(tmp_path)
    index = tmp_path / "registry.yaml"
    index.write_text(
        index.read_text(encoding="utf-8").replace(
            "datasets/documents.odcs.yaml", "../outside.odcs.yaml"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="escapes contract root"):
        FileRegistry(tmp_path).load_odcs("documents")


def test_registry_rejects_absolute_and_symlink_escapes(tmp_path) -> None:
    write_contract_tree(tmp_path)
    absolute = tmp_path / "datasets" / "documents.odcs.yaml"
    index = tmp_path / "registry.yaml"
    original = index.read_text(encoding="utf-8")
    index.write_text(
        original.replace("datasets/documents.odcs.yaml", str(absolute)),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must be relative"):
        FileRegistry(tmp_path).load_odcs("documents")

    outside = tmp_path.parent / "registry-outside.odcs.yaml"
    outside.write_text("id: leaked\nversion: 0.0.0\nschema: []\n", encoding="utf-8")
    link = tmp_path / "datasets" / "leak.odcs.yaml"
    link.symlink_to(outside)
    index.write_text(
        original.replace("datasets/documents.odcs.yaml", "datasets/leak.odcs.yaml"),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="escapes contract root"):
        FileRegistry(tmp_path).load_odcs("documents")

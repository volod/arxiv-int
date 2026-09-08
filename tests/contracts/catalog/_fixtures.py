"""Small ODCS-shaped fixtures for contract primitive tests."""

import pathlib


def write_contract_tree(root: pathlib.Path, semantic_hash: str | None = None) -> None:
    """Write a minimal registry, contract, mapping, and canonical model."""
    fingerprint = ""
    if semantic_hash is not None:
        fingerprint = f'\n    fingerprints:\n      semanticMetadataHash: "{semantic_hash}"'
    (root / "datasets").mkdir(parents=True, exist_ok=True)
    (root / "mappings").mkdir(exist_ok=True)
    (root / "canonical" / "odcs").mkdir(parents=True, exist_ok=True)
    (root / "registry.yaml").write_text(
        "contracts:\n"
        "  documents:\n"
        "    odcs: datasets/documents.odcs.yaml\n"
        "    mapping: mappings/documents.mapping.yaml"
        f"{fingerprint}\n",
        encoding="utf-8",
    )
    (root / "datasets" / "documents.odcs.yaml").write_text(
        "id: documents\n"
        "version: 1.0.0\n"
        "schema:\n"
        "  - properties:\n"
        "      - name: document_id\n"
        "        logicalType: string\n"
        "        physicalType: string\n"
        "        required: true\n",
        encoding="utf-8",
    )
    (root / "mappings" / "documents.mapping.yaml").write_text(
        "metadata:\n"
        "  domain: archive\n"
        "  sourceContract: documents\n"
        "  canonicalEntity: document\n"
        "fieldMappings:\n"
        "  - sourceField: document_id\n"
        "    binding: document.documentId\n"
        "    semanticTerm: urn:arxiv-int:document-id\n",
        encoding="utf-8",
    )
    (root / "canonical" / "model.yaml").write_text(
        "metadata:\n"
        "  canonicalModelRef: urn:arxiv-int:model:1.0.0\n"
        "semanticTerms:\n"
        "  urn:arxiv-int:document-id:\n"
        "    valueType: string\n"
        "entities:\n"
        "  document:\n"
        "    contract: odcs/document.odcs.yaml\n",
        encoding="utf-8",
    )
    (root / "canonical" / "odcs" / "document.odcs.yaml").write_text(
        "schema:\n"
        "  - properties:\n"
        "      - name: document_id\n"
        "        required: true\n"
        "        customProperties:\n"
        "          - property: canonicalBinding\n"
        "            value:\n"
        "              binding: document.documentId\n"
        "              semanticTerm: urn:arxiv-int:document-id\n",
        encoding="utf-8",
    )

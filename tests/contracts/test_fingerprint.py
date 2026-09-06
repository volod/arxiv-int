"""Semantic fingerprint behavior."""

import copy

import pytest

from arxiv_int.contracts.fingerprint import semantic_metadata, semantic_metadata_hash

_MAPPING = {
    "metadata": {
        "domain": "archive",
        "sourceContract": "documents",
        "canonicalEntity": "document",
    },
    "fieldMappings": [
        {
            "sourceField": "document_id",
            "binding": "document.documentId",
            "semanticTerm": "urn:arxiv-int:document-id",
        }
    ],
}


def test_hash_is_stable_for_known_metadata() -> None:
    assert semantic_metadata_hash(_MAPPING) == (
        "06516e17c50933e9305b3e3fafb54c991ec66ed1817390badd8184535ce1f8e9"
    )


def test_hash_ignores_order_and_cosmetic_domain() -> None:
    reordered = {
        "fieldMappings": copy.deepcopy(_MAPPING["fieldMappings"]),
        "metadata": {
            "canonicalEntity": "document",
            "sourceContract": "documents",
            "domain": "another-display-name",
        },
    }
    assert semantic_metadata_hash(reordered) == semantic_metadata_hash(_MAPPING)


def test_hash_changes_when_binding_changes() -> None:
    changed = copy.deepcopy(_MAPPING)
    changed["fieldMappings"][0]["binding"] = "document.externalId"
    assert semantic_metadata_hash(changed) != semantic_metadata_hash(_MAPPING)


def test_preserves_unknown_metadata_and_rejects_duplicates() -> None:
    enriched = copy.deepcopy(_MAPPING)
    enriched["metadata"]["reviewerNote"] = "keep"
    enriched["fieldMappings"][0]["x-arxiv-int-note"] = "retain"
    blocks = semantic_metadata(enriched)
    assert blocks["contract"]["reviewerNote"] == "keep"
    assert blocks["field:document_id"]["x-arxiv-int-note"] == "retain"
    assert semantic_metadata_hash(enriched) != semantic_metadata_hash(_MAPPING)

    duplicate_source = copy.deepcopy(_MAPPING)
    duplicate_source["fieldMappings"].append(
        {
            "sourceField": "document_id",
            "binding": "document.other",
            "semanticTerm": "urn:arxiv-int:other",
        }
    )
    with pytest.raises(ValueError, match="duplicate field mapping"):
        semantic_metadata_hash(duplicate_source)

    ambiguous = copy.deepcopy(_MAPPING)
    ambiguous["fieldMappings"].append(
        {
            "sourceField": "alt_id",
            "binding": "document.documentId",
            "semanticTerm": "urn:arxiv-int:document-id",
        }
    )
    with pytest.raises(ValueError, match="ambiguous binding"):
        semantic_metadata_hash(ambiguous)

    malformed = copy.deepcopy(_MAPPING)
    malformed["fieldMappings"].append({"binding": "document.missingSource"})
    with pytest.raises(ValueError, match="missing required sourceField"):
        semantic_metadata_hash(malformed)

    unknown_only = copy.deepcopy(_MAPPING)
    unknown_only["fieldMappings"].append({"extensionOnly": True})
    assert semantic_metadata_hash(unknown_only) == semantic_metadata_hash(_MAPPING)

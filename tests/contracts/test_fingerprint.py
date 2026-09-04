"""Semantic fingerprint behavior inherited from the fl-op seam."""

import copy

from arxiv_int.contracts.fingerprint import semantic_metadata_hash

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


def test_hash_matches_pinned_upstream_algorithm() -> None:
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

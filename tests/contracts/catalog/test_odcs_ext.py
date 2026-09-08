"""ODCS extension helper tests."""

import pytest

from arxiv_int.contracts.catalog.odcs_ext import (
    canonical_binding,
    custom_property,
    project_extension,
)


def test_project_extension_and_nested_binding() -> None:
    properties = [
        {
            "property": "x-arxiv-int",
            "value": {
                "canonicalBinding": {
                    "binding": "document.documentId",
                    "semanticTerm": "urn:arxiv-int:term:document-id",
                    "note": "keep",
                }
            },
        }
    ]
    extension = project_extension(properties)
    assert extension is not None
    binding = canonical_binding(properties)
    assert binding is not None
    assert binding["binding"] == "document.documentId"
    assert binding["note"] == "keep"


def test_legacy_canonical_binding_still_works() -> None:
    properties = [
        {
            "property": "canonicalBinding",
            "value": {
                "binding": "document.documentId",
                "semanticTerm": "urn:arxiv-int:term:document-id",
            },
        }
    ]
    assert canonical_binding(properties)["binding"] == "document.documentId"


def test_malformed_custom_property_is_rejected() -> None:
    with pytest.raises(ValueError, match="must be a mapping"):
        custom_property([{"property": "x-arxiv-int", "value": "nope"}], "x-arxiv-int")

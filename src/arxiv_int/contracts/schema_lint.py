"""Official ODCS JSON Schema validation for dataset contracts."""

import json
import pathlib
from collections.abc import Sequence
from typing import Any

from arxiv_int.contracts._yaml import load_mapping
from arxiv_int.features import require_module

ODCS_SCHEMA_RELATIVE = pathlib.Path("odcs") / "odcs-json-schema-v3.1.0.json"


def odcs_schema_path(contracts_root: pathlib.Path) -> pathlib.Path:
    """Return the vendored official ODCS 3.1.0 JSON Schema path."""
    return contracts_root / ODCS_SCHEMA_RELATIVE


def load_odcs_json_schema(contracts_root: pathlib.Path) -> dict[str, Any]:
    """Load the pinned official ODCS JSON Schema document."""
    path = odcs_schema_path(contracts_root)
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError(f"ODCS JSON Schema is not an object: {path}")
    return document


def validate_odcs_documents(
    contracts_root: pathlib.Path,
    documents: Sequence[tuple[str, dict[str, Any]]],
) -> list[str]:
    """Validate ODCS documents against the official JSON Schema.

    Returns human-readable finding strings; an empty list means success.
    """
    jsonschema = require_module("jsonschema")
    schema = load_odcs_json_schema(contracts_root)
    validator_cls = jsonschema.validators.validator_for(schema)
    validator_cls.check_schema(schema)
    validator = validator_cls(schema)
    findings: list[str] = []
    for label, document in documents:
        errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
        for error in errors:
            path = ".".join(str(part) for part in error.path) or "<root>"
            findings.append(f"{label}: ODCS schema error at {path}: {error.message}")
    return findings


def validate_dataset_files(contracts_root: pathlib.Path) -> list[str]:
    """Validate every ``datasets/*.odcs.yaml`` file under the contracts root."""
    dataset_dir = contracts_root / "datasets"
    if not dataset_dir.is_dir():
        return [f"missing datasets directory: {dataset_dir}"]
    documents: list[tuple[str, dict[str, Any]]] = []
    for path in sorted(dataset_dir.glob("*.odcs.yaml")):
        documents.append((str(path.relative_to(contracts_root)), load_mapping(path)))
    if not documents:
        return [f"no ODCS dataset files under {dataset_dir}"]
    return validate_odcs_documents(contracts_root, documents)

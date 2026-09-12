"""Classification snapshot identities, layout, and checksum validation."""

from pathlib import Path
from typing import Any

from arxiv_int.pipeline.lake.artifacts import validate_snapshot_manifest

SCHEMA = "arxiv-int.file-classification.v1"
CONTRACT_VERSION = "1.0.0"
FILE_CLASSIFICATIONS = "file-classifications"
CLASSIFICATION_CLASSES = "classification-classes"
MANIFEST_KIND = "manifest"
CLASSIFICATIONS_KIND = "file-classifications"
CLASSES_KIND = "classification-classes"

LAYOUT: dict[str, str] = {
    CLASSIFICATIONS_KIND: "normalized/classifications",
    CLASSES_KIND: "normalized/classification-classes",
    MANIFEST_KIND: "normalized/classification",
}
DATASETS: dict[str, str] = {
    FILE_CLASSIFICATIONS: CLASSIFICATIONS_KIND,
    CLASSIFICATION_CLASSES: CLASSES_KIND,
}


def validate_manifest(path: Path, digest: str) -> dict[str, Any]:
    """Rehash every classification artifact before reuse."""
    return validate_snapshot_manifest(path, digest, label="classification")

"""Validate an externally published classification snapshot before cache reuse."""

import json
from pathlib import Path

from arxiv_int.classification.artifacts import (
    CLASSIFICATION_CLASSES,
    FILE_CLASSIFICATIONS,
    validate_manifest,
)


def validate_classification_output(directory: Path) -> None:
    """Refuse a classify cache hit when its output changed or lost completeness."""
    payload = json.loads((directory / "stage.json").read_text(encoding="ascii"))
    if payload.get("stage") != "classify":
        return
    outputs = payload.get("outputs", [])
    if [output.get("dataset") for output in outputs] != [
        FILE_CLASSIFICATIONS,
        CLASSIFICATION_CLASSES,
    ]:
        raise ValueError("missing classification outputs")
    partition = outputs[0].get("partition", {})
    if any(output.get("partition") != partition for output in outputs):
        raise ValueError("classification outputs refer to different snapshots")
    manifest = Path(partition["manifest"])
    if manifest.resolve() != manifest:
        raise ValueError("symlinked classification output")
    summary = validate_manifest(manifest, partition["sha256"])
    generation = summary["generation_id"]
    if any(output["generationId"] != generation for output in outputs):
        raise ValueError("classification output generation mismatch")
    accounting = summary["accounting"]
    if (
        accounting["classified_rows"] != accounting["physical_inventory_rows"]
        or accounting["classified_rows"] != summary["file_classifications"]
        or accounting["classified_rows"] != sum(summary["counts_by_primary"].values())
    ):
        raise ValueError("classification output accounting mismatch")

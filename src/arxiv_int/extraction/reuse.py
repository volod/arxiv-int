"""Validate external extraction artifacts referenced by a stage attempt."""

import json
from pathlib import Path


def validate_extraction_output(directory: Path) -> None:
    """Require both contract outputs to share one valid extraction manifest."""
    payload = json.loads((directory / "stage.json").read_text(encoding="ascii"))
    if payload.get("stage") != "extract":
        return
    from arxiv_int.extraction.artifacts import validate_manifest

    outputs = payload.get("outputs", [])
    if [output.get("dataset") for output in outputs] != ["documents", "spans"]:
        raise ValueError("missing extraction outputs")
    partitions = [output.get("partition", {}) for output in outputs]
    if partitions[0] != partitions[1]:
        raise ValueError("extraction outputs do not share one manifest")
    manifest = Path(partitions[0]["manifest"])
    if manifest.resolve() != manifest:
        raise ValueError("symlinked extraction output")
    summary = validate_manifest(manifest, partitions[0]["sha256"])
    if any(summary["generation_id"] != output["generationId"] for output in outputs):
        raise ValueError("extraction output generation mismatch")

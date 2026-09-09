"""Validate external normalization artifacts referenced by a stage attempt."""

import json
from pathlib import Path


def validate_normalization_output(directory: Path) -> None:
    """Require the published normalized-documents output to still validate."""
    payload = json.loads((directory / "stage.json").read_text(encoding="ascii"))
    if payload.get("stage") != "normalize":
        return
    from arxiv_int.pipeline.normalize.artifacts import validate_manifest

    outputs = payload.get("outputs", [])
    if [output.get("dataset") for output in outputs] != ["normalized-documents"]:
        raise ValueError("missing normalization outputs")
    partition = outputs[0].get("partition", {})
    manifest = Path(partition["manifest"])
    if manifest.resolve() != manifest:
        raise ValueError("symlinked normalization output")
    summary = validate_manifest(manifest, partition["sha256"])
    if summary["generation_id"] != outputs[0]["generationId"]:
        raise ValueError("normalization output generation mismatch")

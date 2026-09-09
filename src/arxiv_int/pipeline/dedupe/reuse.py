"""Validate external duplicate-grouping artifacts referenced by a stage attempt."""

import json
from pathlib import Path


def validate_dedupe_output(directory: Path) -> None:
    """Require the published duplicate-groups output to still validate."""
    payload = json.loads((directory / "stage.json").read_text(encoding="ascii"))
    if payload.get("stage") != "dedupe":
        return
    from arxiv_int.pipeline.dedupe.artifacts import validate_manifest

    outputs = payload.get("outputs", [])
    if [output.get("dataset") for output in outputs] != ["duplicate-groups"]:
        raise ValueError("missing duplicate-groups outputs")
    partition = outputs[0].get("partition", {})
    manifest = Path(partition["manifest"])
    if manifest.resolve() != manifest:
        raise ValueError("symlinked duplicate-groups output")
    summary = validate_manifest(manifest, partition["sha256"])
    if summary["generation_id"] != outputs[0]["generationId"]:
        raise ValueError("duplicate-groups output generation mismatch")

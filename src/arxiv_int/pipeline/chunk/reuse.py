"""Validate external chunk artifacts referenced by a stage attempt."""

import json
from pathlib import Path


def validate_chunk_output(directory: Path) -> None:
    """Require the published chunks output to still validate."""
    payload = json.loads((directory / "stage.json").read_text(encoding="ascii"))
    if payload.get("stage") != "chunk":
        return
    from arxiv_int.pipeline.chunk.artifacts import validate_manifest

    outputs = payload.get("outputs", [])
    if [output.get("dataset") for output in outputs] != ["chunks"]:
        raise ValueError("missing chunk outputs")
    partition = outputs[0].get("partition", {})
    manifest = Path(partition["manifest"])
    if manifest.resolve() != manifest:
        raise ValueError("symlinked chunk output")
    summary = validate_manifest(manifest, partition["sha256"])
    if summary["generation_id"] != outputs[0]["generationId"]:
        raise ValueError("chunk output generation mismatch")

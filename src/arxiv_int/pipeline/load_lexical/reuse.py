"""Validate external lexical load artifacts referenced by a stage attempt."""

import json
from pathlib import Path


def validate_load_lexical_output(directory: Path) -> None:
    """Require the published lexical load manifest to still validate."""
    payload = json.loads((directory / "stage.json").read_text(encoding="ascii"))
    if payload.get("stage") != "load-lexical":
        return
    from arxiv_int.pipeline.load_lexical.artifacts import DATASET, validate_manifest

    outputs = payload.get("outputs", [])
    if [output.get("dataset") for output in outputs] != [DATASET]:
        raise ValueError("missing lexical load outputs")
    partition = outputs[0].get("partition", {})
    manifest = Path(partition["manifest"])
    if manifest.resolve() != manifest:
        raise ValueError("symlinked lexical load output")
    summary = validate_manifest(manifest, partition["sha256"])
    if summary["generation_id"] != outputs[0]["generationId"]:
        raise ValueError("lexical load output generation mismatch")
    if not summary["reconciliation"]["ok"]:
        raise ValueError("lexical load output did not reconcile")

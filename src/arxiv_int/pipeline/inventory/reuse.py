"""Validate external inventory artifacts referenced by a published stage attempt."""

import json
from pathlib import Path


def validate_inventory_output(directory: Path) -> None:
    """Inventory cache acceptance includes every external Parquet and metadata checksum."""
    payload = json.loads((directory / "stage.json").read_text(encoding="ascii"))
    if payload.get("stage") != "inventory":
        return
    from arxiv_int.pipeline.inventory.publish import validate_manifest

    outputs = payload.get("outputs", [])
    if len(outputs) != 1 or outputs[0]["dataset"] != "source-occurrences":
        raise ValueError("missing inventory output")
    output = outputs[0]
    partition = output["partition"]
    manifest = Path(partition["manifest"])
    if manifest.resolve() != manifest:
        raise ValueError("symlinked inventory output")
    summary = validate_manifest(manifest, partition["sha256"])
    if summary["generation_id"] != output["generationId"]:
        raise ValueError("inventory output generation mismatch")

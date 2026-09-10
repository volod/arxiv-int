"""Duplicate-group snapshot layout and external artifact validation."""

from pathlib import Path
from typing import Any

from arxiv_int.pipeline.lake.artifacts import validate_snapshot_manifest

SCHEMA = "arxiv-int.duplicate-grouping.v1"
CONTRACT = "duplicate-groups"
GROUPS_KIND = "duplicate-groups"
MANIFEST_KIND = "manifest"

LAYOUT: dict[str, str] = {
    GROUPS_KIND: "normalized/duplicate-groups",
    MANIFEST_KIND: "normalized/dedupe",
}
DATASETS: dict[str, str] = {CONTRACT: GROUPS_KIND}
PAIRS_FILE = "pairs.jsonl"


def validate_manifest(path: Path, digest: str) -> dict[str, Any]:
    """Rehash every duplicate-grouping artifact before reuse."""
    return validate_snapshot_manifest(path, digest, label="dedupe")

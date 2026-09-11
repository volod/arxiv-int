"""Write the run-scoped lexical load manifest under ``$RUNS_DIR``."""

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.inventory.publish import atomic_json
from arxiv_int.pipeline.load_lexical.artifacts import SCHEMA, manifest_path
from arxiv_int.pipeline.load_lexical.loader import LoadCounts
from arxiv_int.pipeline.load_lexical.reconcile import Reconciliation
from arxiv_int.stores.projections.adapters.lexical import (
    INDEXED_COLUMNS,
    TOKENIZER_FINGERPRINT,
)
from arxiv_int.stores.projections.model import KindBuild


def load_summary(
    *,
    generation_id: str,
    build: KindBuild,
    loads: Sequence[LoadCounts],
    reconciliation: Reconciliation,
    upstream: Mapping[str, Mapping[str, str]],
    index_bytes: Mapping[str, int],
    activated: bool,
) -> dict[str, Any]:
    """Build the content-free lexical load manifest summary."""
    return {
        "schema": SCHEMA,
        "generation_id": generation_id,
        "activated": activated,
        "index": {
            "engine": build.engine,
            "engine_object": build.engine_object,
            "indexed_columns": list(INDEXED_COLUMNS),
            "tokenizer_fingerprint": TOKENIZER_FINGERPRINT,
            **{name: int(value) for name, value in sorted(index_bytes.items())},
        },
        "loads": [item.as_json_dict() for item in loads],
        "projection": {
            "checksum": build.checksum,
            "projection_id": build.projection_id,
            "quality_status": build.quality_status,
            "row_count": build.row_count,
            "status": build.status,
            "version_id": build.version_id,
        },
        "reconciliation": reconciliation.as_json_dict(),
        "upstream": {name: dict(value) for name, value in sorted(upstream.items())},
    }


def publish_summary(runs_dir: Path, run_id: str, summary: Mapping[str, Any]) -> tuple[Path, str]:
    """Write the manifest atomically and return its path and checksum."""
    path = manifest_path(runs_dir, run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_json(path, dict(summary))
    return path, hash_file(path)[0]

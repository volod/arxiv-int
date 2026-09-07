"""Redacted migration evidence written under DATA_DIR/migrations/<run-id>/."""

import json
from pathlib import Path
from typing import Any

from arxiv_int.contracts.migrations.paths import migration_artifact_dir
from arxiv_int.contracts.migrations.runner import redact_url
from arxiv_int.stores.postgres.inspect_live import LiveStoreCatalog


def catalog_as_dict(catalog: LiveStoreCatalog) -> dict[str, Any]:
    """Return a JSON-safe catalog snapshot."""
    return {
        "schemas": list(catalog.schemas),
        "partitioned": [
            {
                "name": item.qualified_name,
                "strategy": item.strategy,
                "child_count": item.child_count,
            }
            for item in catalog.partitioned
        ],
        "checks": list(catalog.checks),
        "roles": list(catalog.roles),
        "staging_tables": list(catalog.staging_tables),
        "revision": catalog.revision,
        "extensions": list(catalog.extensions),
        "control_tables": list(catalog.control_tables),
    }


def write_evidence(
    project_root: Path,
    payload: dict[str, Any],
    *,
    run_id: str,
) -> Path:
    """Write secret-free JSON evidence for one migration or adoption run."""
    redacted = dict(payload)
    if "url" in redacted and isinstance(redacted["url"], str):
        redacted["url"] = redact_url(redacted["url"])
    destination = migration_artifact_dir(project_root, run_id)
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "live-schema.json"
    path.write_text(json.dumps(redacted, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path

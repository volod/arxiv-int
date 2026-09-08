"""Identity-free export receipts and local diagnostic maps."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from arxiv_int.evaluation.bundles.layout import digest_bytes
from arxiv_int.evaluation.export.catalog import IdentityCatalog, catalog_as_json
from arxiv_int.evaluation.export.io import relative_destination, write_json, write_policy_copy
from arxiv_int.evaluation.export.map import SubstitutionTable
from arxiv_int.evaluation.export.paths import export_artifact_dir
from arxiv_int.evaluation.export.policy import (
    DATA_CLASS_TRANSFORMED,
    POLICY_ID,
    POLICY_VERSION,
    policy_fingerprint,
)


def build_receipt(
    *,
    source_fingerprint: str,
    files: Sequence[tuple[str, Path]],
    transformed: Mapping[str, bytes],
    destination_root: Path | None,
    project_root: Path,
) -> dict[str, object]:
    """Return an identity-free receipt for Git or DATA_DIR."""
    root = destination_root or project_root
    records = []
    hashed: list[tuple[str, str, int]] = []
    for source_name, destination in files:
        payload = transformed[source_name]
        digest = digest_bytes(payload)
        relative = relative_destination(destination, root)
        records.append(
            {
                "bytes": len(payload),
                "destination": relative,
                "sha256": digest,
                "source": source_name,
            }
        )
        hashed.append((relative, digest, len(payload)))
    policy = policy_fingerprint()
    material = json.dumps(
        {"files": hashed, "policy_fingerprint": policy},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")
    return {
        "data_class": DATA_CLASS_TRANSFORMED,
        "export_fingerprint": digest_bytes(material),
        "files": records,
        "policy_fingerprint": policy,
        "policy_id": POLICY_ID,
        "policy_version": POLICY_VERSION,
        "source_bundle_fingerprint": source_fingerprint,
        "transformed_identities": True,
    }


def write_diagnostics(
    *,
    project_root: Path,
    run_id: str,
    catalog: IdentityCatalog,
    table: SubstitutionTable,
    receipt: Mapping[str, object],
) -> Path:
    """Write the local identity map, receipt, and policy copy under DATA_DIR."""
    diagnostics = export_artifact_dir(project_root, run_id)
    diagnostics.mkdir(parents=True, exist_ok=True)
    write_json(diagnostics / "receipt.json", dict(receipt))
    write_json(
        diagnostics / "identity-map.json",
        {"catalog": catalog_as_json(catalog), "substitutions": table.reference_map},
    )
    write_policy_copy(diagnostics / "policy.json")
    return diagnostics

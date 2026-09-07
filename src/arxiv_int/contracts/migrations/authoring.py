"""Generate candidate immutable revisions from contract metadata changes."""

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arxiv_int.contracts.migrations.paths import (
    head_state_path,
    revision_manifest_path,
    versions_dir,
)
from arxiv_int.contracts.migrations.render import render_revision
from arxiv_int.contracts.migrations.state import (
    SchemaOperation,
    contract_state,
    diff_states,
    load_state,
    write_state,
)
from arxiv_int.contracts.registry import FileRegistry
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel, load_schema_model

_SLUG = re.compile(r"[^a-z0-9]+")
REVISION_WIDTH = 4


@dataclass(frozen=True)
class RevisionCandidate:
    """One generated revision plus the operations it freezes."""

    revision: str
    path: Path
    operations: tuple[SchemaOperation, ...]

    @property
    def created(self) -> bool:
        """Return whether a revision file was written."""
        return bool(self.operations)


def slug(message: str) -> str:
    """Return a stable file slug for a revision message."""
    return _SLUG.sub("_", message.strip().lower()).strip("_") or "revision"


def read_manifest(project_root: Path) -> dict[str, Any]:
    """Load the revision checksum manifest, treating a missing file as empty."""
    path = revision_manifest_path(project_root)
    if not path.is_file():
        return {"revisions": {}}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict) or not isinstance(loaded.get("revisions"), dict):
        raise ValueError(f"revision manifest is not an object: {path}")
    return loaded


def file_checksum(path: Path) -> str:
    """Return the SHA-256 digest of one revision file."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_manifest(project_root: Path, manifest: dict[str, Any]) -> Path:
    path = revision_manifest_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def next_revision_id(manifest: dict[str, Any]) -> str:
    """Return the next zero-padded revision id; ids are never reused."""
    existing = [int(item) for item in manifest["revisions"] if item.isdigit()]
    return str(max(existing, default=0) + 1).zfill(REVISION_WIDTH)


def head_revision(manifest: dict[str, Any]) -> str | None:
    """Return the single head revision recorded by the manifest."""
    revisions = manifest["revisions"]
    parents = {spec.get("downRevision") for spec in revisions.values()}
    heads = sorted(set(revisions) - {item for item in parents if item})
    if not heads:
        return None
    if len(heads) > 1:
        raise ValueError(f"revision manifest has multiple heads: {', '.join(heads)}")
    return str(heads[0])


def contract_fingerprints(registry: FileRegistry, model: ContractSchemaModel) -> dict[str, str]:
    """Return reviewed contract identity pinned into a generated revision."""
    fingerprints: dict[str, str] = {}
    for table in model.tables:
        entry = registry.get_entry(table.contract_id)
        fingerprints[table.contract_id] = (
            f"{table.odcs_id}@{table.version}:{entry.stored_semantic_hash or 'unmapped'}"
        )
    return fingerprints


def generate_revision(
    project_root: Path,
    contracts_root: Path,
    *,
    message: str = "contract schema change",
) -> RevisionCandidate:
    """Diff contract metadata against the frozen head state and write a candidate revision."""
    registry = FileRegistry(contracts_root)
    model = load_schema_model(registry)
    before = load_state(head_state_path(project_root))
    after = contract_state(model)
    operations = diff_states(before, after)
    manifest = read_manifest(project_root)
    parent = head_revision(manifest)
    if not operations:
        return RevisionCandidate(parent or "", head_state_path(project_root), ())
    revision = next_revision_id(manifest)
    destination = versions_dir(project_root) / f"{revision}_{slug(message)}.py"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        render_revision(
            revision=revision,
            down_revision=parent,
            message=message,
            operations=operations,
            before=before,
            after=after,
            fingerprints=contract_fingerprints(registry, model),
        ),
        encoding="utf-8",
    )
    manifest["revisions"][revision] = {
        "file": destination.name,
        "downRevision": parent,
        "sha256": file_checksum(destination),
        "message": message,
    }
    _write_manifest(project_root, manifest)
    write_state(head_state_path(project_root), after, revision=revision)
    return RevisionCandidate(revision, destination, operations)

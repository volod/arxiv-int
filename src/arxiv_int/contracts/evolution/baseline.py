"""Reviewed evolution baselines under contracts/evolution/."""

import json
import pathlib
from typing import Any

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.contracts.evolution.core import freeze_baseline, schema_snapshot
from arxiv_int.contracts.evolution.policy import projection_snapshot
from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.contracts.generate.pipeline import GENERATOR_VERSION

EVOLUTION_DIRNAME = "evolution"


def evolution_root(contracts_root: pathlib.Path) -> pathlib.Path:
    """Return the reviewed baseline directory."""
    return contracts_root / EVOLUTION_DIRNAME


def baseline_path(contracts_root: pathlib.Path, contract_id: str) -> pathlib.Path:
    """Return the baseline JSON path for one contract."""
    return evolution_root(contracts_root) / f"{contract_id}.json"


def load_baseline(path: pathlib.Path) -> dict[str, Any]:
    """Load one reviewed baseline document."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Evolution baseline is not an object: {path}")
    return loaded


def _artifact_fingerprint(path: pathlib.Path) -> str | None:
    if not path.is_file():
        return None
    return sha256_text(path.read_text(encoding="utf-8"))


def build_reviewed_snapshot(
    registry: FileRegistry,
    contract_id: str,
    *,
    generated_root: pathlib.Path | None = None,
) -> dict[str, Any]:
    """Build a reviewed snapshot from ODCS, mapping, and generated artifacts."""
    odcs = registry.load_odcs(contract_id)
    entry = registry.get_entry(contract_id)
    semantic = entry.stored_semantic_hash
    if entry.mapping_ref is not None and semantic is None:
        semantic = registry.semantic_fingerprint(contract_id)
    generated = generated_root or (registry.root / "generated")
    fingerprints = {
        "semanticMetadataHash": semantic or "",
        "generatorVersion": GENERATOR_VERSION,
        "avroSha256": _artifact_fingerprint(generated / "avro" / f"{contract_id}.avsc") or "",
        "postgresSha256": _artifact_fingerprint(generated / "postgres" / f"{contract_id}.sql")
        or "",
    }
    snapshot = schema_snapshot(odcs, contract_id, fingerprints=fingerprints)
    snapshot["projections"] = projection_snapshot(odcs)
    return snapshot


def freeze_contract_baseline(
    contracts_root: pathlib.Path,
    contract_id: str,
    *,
    generated_root: pathlib.Path | None = None,
) -> pathlib.Path:
    """Freeze or append the reviewed baseline for one registered contract."""
    registry = FileRegistry(contracts_root)
    snapshot = build_reviewed_snapshot(registry, contract_id, generated_root=generated_root)
    return freeze_baseline(baseline_path(contracts_root, contract_id), snapshot)


def freeze_all_baselines(contracts_root: pathlib.Path) -> tuple[pathlib.Path, ...]:
    """Freeze baselines for every registered contract."""
    registry = FileRegistry(contracts_root)
    return tuple(
        freeze_contract_baseline(contracts_root, contract_id)
        for contract_id in registry.contract_ids()
    )

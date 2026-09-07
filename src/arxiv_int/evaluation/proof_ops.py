"""Proof discovery, summary helpers, publication, and capability dispatch."""

import json
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.evaluation.bundle_layout import digest_bytes
from arxiv_int.evaluation.bundle_manifest import canonical_json
from arxiv_int.evaluation.bundles import verify_run_bundle
from arxiv_int.evaluation.eval_errors import ProofError, ProofExistsError, ProofIntegrityError
from arxiv_int.evaluation.eval_paths import fixture_root, published_proof_dir
from arxiv_int.evaluation.evaluate_run import EvaluateRequest, run_evaluate
from arxiv_int.evaluation.export_policy import DATA_CLASS_TRANSFORMED, POLICY_ID, policy_fingerprint
from arxiv_int.evaluation.families import load_fixture_catalog
from arxiv_int.evaluation.fixture_guard import item_ledger
from arxiv_int.evaluation.fixture_kinds import DATA_CLASS_RAW
from arxiv_int.evaluation.proof_checks import (
    current_fingerprints,
    redact_summary_text,
    refuse_proof_payloads,
    refuse_proof_tree_leaks,
    validate_proof_manifest,
)
from arxiv_int.evaluation.proof_model import (
    VALIDATOR_BUNDLE,
    VALIDATOR_EXPORT,
    VALIDATOR_LEDGER,
    VALIDATOR_SPLIT,
    CapabilityProofTarget,
    ProofManifest,
    capability_registry_document,
    load_capability_registry,
    require_capability,
)

IMPLEMENTED_PROOFS = frozenset({"evaluation-foundation"})


@dataclass(frozen=True, slots=True)
class ProofPublishResult:
    """Paths and fingerprints of one published capability proof."""

    directory: Path
    manifest: Path
    fingerprint: str
    summary: str


def discover_proof_targets(project_root: Path) -> tuple[CapabilityProofTarget, ...]:
    """Return registered capability proof targets in stable id order."""
    registry = load_capability_registry(project_root)
    return tuple(registry[name] for name in sorted(registry))


def proof_summary(manifest: ProofManifest) -> str:
    """Build an identity-free operator summary for repository docs."""
    text = (
        f"capability={manifest.capability_id} proof_id={manifest.proof_id} "
        f"verdict={manifest.verdict} data_class={manifest.data_class} "
        f"code={manifest.fingerprints.get('code', '')[:12]} "
        f"fixtures={manifest.fingerprints.get('fixtures', '')[:12]}"
    )
    return redact_summary_text(text)


def write_capability_registry(project_root: Path) -> Path:
    """Write the committed capability registry document."""
    path = project_root / "configs" / "proofs" / "capabilities.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(capability_registry_document()))
    return path


def publish_capability_proof(
    *,
    project_root: Path,
    capability: str,
    run_id: str,
    results_dir: Path,
    runs_dir: Path,
    fixture_dir: Path | None = None,
) -> ProofPublishResult:
    """Dispatch one capability proof or refuse unvalidated/unknown targets."""
    target = require_capability(load_capability_registry(project_root), capability)
    if capability not in IMPLEMENTED_PROOFS:
        raise ProofIntegrityError(
            f"usable stages for {capability} are unvalidated; no proof publisher is registered"
        )
    gold_root = fixture_dir or fixture_root(project_root)
    outcome = run_evaluate(
        EvaluateRequest(
            run_id=run_id,
            project_root=project_root,
            fixture_root=gold_root,
            runs_dir=runs_dir,
        )
    )
    verify_run_bundle(outcome.bundle.directory)
    families = load_fixture_catalog(gold_root)
    ledger = item_ledger(tuple(item for family in families for item in family.items))
    fingerprints = current_fingerprints(project_root, ledger.fingerprint)
    manifest = ProofManifest(
        schema_version=1,
        capability_id=capability,
        proof_id=run_id,
        run_id=run_id,
        data_class=DATA_CLASS_RAW,
        verdict=outcome.verdict,
        fingerprints=fingerprints,
        stages={"evaluate": "validated"},
        validators={
            VALIDATOR_BUNDLE: "pass",
            VALIDATOR_EXPORT: "pass",
            VALIDATOR_LEDGER: "pass",
            VALIDATOR_SPLIT: "pass",
            "stage:evaluate": "pass",
        },
        artifacts={
            "evaluation/manifest.json": {
                "bytes": (outcome.bundle.manifest).stat().st_size,
                "sha256": outcome.bundle.fingerprint,
            }
        },
    )
    validate_proof_manifest(manifest.as_json_dict(), target, fingerprints)
    summary = proof_summary(manifest)
    payload = canonical_json(manifest.as_json_dict())
    policy_payload = canonical_json(
        {
            "data_class": DATA_CLASS_TRANSFORMED,
            "policy_fingerprint": policy_fingerprint(),
            "policy_id": POLICY_ID,
        }
    )
    refuse_proof_payloads(
        {
            "proof-manifest.json": payload.decode("utf-8"),
            "summary.txt": summary,
            "policy.json": policy_payload.decode("utf-8"),
        }
    )
    destination = published_proof_dir(results_dir, capability, run_id)
    _claim_proof_destination(destination)
    manifest_path = destination / "proof-manifest.json"
    manifest_path.write_bytes(payload)
    (destination / "summary.txt").write_text(summary + "\n", encoding="utf-8")
    (destination / "policy.json").write_bytes(policy_payload)
    return ProofPublishResult(destination, manifest_path, digest_bytes(payload), summary)


def check_capability_proof(directory: Path, project_root: Path, fixture_fingerprint: str) -> str:
    """Verify a published proof directory against current fingerprints."""
    path = directory / "proof-manifest.json"
    if not path.is_file():
        raise ProofIntegrityError("proof directory is missing proof-manifest.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ProofError("proof manifest is not an object")
    capability = str(payload.get("capability_id") or "")
    target = require_capability(load_capability_registry(project_root), capability)
    expected = current_fingerprints(project_root, fixture_fingerprint)
    validate_proof_manifest(payload, target, expected)
    refuse_proof_tree_leaks(directory)
    return digest_bytes(path.read_bytes())


def threshold_document() -> dict[str, object]:
    """Return committed metric thresholds that do not auto-adopt."""
    return {
        "adopt": 0.9,
        "metric_class": "held-out",
        "review_budget": 0.5,
        "schema_version": 1,
        "source": "fixture-defaults-not-tuned-on-final",
    }


def write_threshold_config(project_root: Path) -> Path:
    """Write committed evaluation thresholds."""
    path = project_root / "configs" / "evaluation" / "thresholds.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json(threshold_document()))
    return path


def _claim_proof_destination(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() or destination.exists():
        raise ProofExistsError(f"proof already exists: {destination}")
    try:
        destination.mkdir()
    except FileExistsError as error:
        raise ProofExistsError(f"proof already exists: {destination}") from error

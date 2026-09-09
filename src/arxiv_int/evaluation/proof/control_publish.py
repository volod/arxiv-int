"""Publish a path-free pipeline-control proof bundle under the configured results root."""

from pathlib import Path

from arxiv_int.evaluation.bundles.layout import digest_bytes
from arxiv_int.evaluation.bundles.manifest import canonical_json
from arxiv_int.evaluation.evaluate.errors import ProofIntegrityError
from arxiv_int.evaluation.evaluate.paths import proof_work_dir, published_proof_dir
from arxiv_int.evaluation.fixtures.kinds import DATA_CLASS_RAW
from arxiv_int.evaluation.proof.checks import refuse_proof_payloads, validate_proof_manifest
from arxiv_int.evaluation.proof.control_copy import (
    CAPABILITY_ID,
    ProofWorkspace,
    prepare_workspace,
    resolve_source_silos,
)
from arxiv_int.evaluation.proof.control_gates import all_gates_passed, evaluate_gates
from arxiv_int.evaluation.proof.control_model import ControlScenarioReport, ShardDelta
from arxiv_int.evaluation.proof.control_registry import control_proof_fingerprints
from arxiv_int.evaluation.proof.control_scenario import run_control_scenario
from arxiv_int.evaluation.proof.model import (
    VALIDATOR_CHECKSUMS,
    VALIDATOR_STAGE,
    ProofManifest,
    load_capability_registry,
    require_capability,
)
from arxiv_int.evaluation.proof.ops import (
    FINGERPRINT_FILENAME,
    ProofPublishResult,
    fingerprint_document,
    proof_summary,
)


def publish_pipeline_control_proof(
    *,
    project_root: Path,
    proof_id: str,
    results_dir: Path,
    archive_dir: Path | None = None,
) -> ProofPublishResult:
    """Run the control scenario on a disposable copy and publish the proof bundle."""
    sources = resolve_source_silos(project_root, archive_dir)
    work = proof_work_dir(results_dir, CAPABILITY_ID, proof_id)
    workspace = prepare_workspace(work, sources, project_root)
    report = run_control_scenario(workspace, project_root, proof_id, sources)
    return write_control_proof(
        project_root=project_root,
        results_dir=results_dir,
        workspace=workspace,
        report=report,
    )


def write_control_proof(
    *,
    project_root: Path,
    results_dir: Path,
    workspace: ProofWorkspace,
    report: ControlScenarioReport,
) -> ProofPublishResult:
    """Validate gates and write the published proof directory."""
    del workspace
    gates = evaluate_gates(report)
    if not all_gates_passed(gates):
        failed = ", ".join(name for name, status in gates.items() if status != "pass")
        raise ProofIntegrityError(f"pipeline-control proof gates failed: {failed}")
    fingerprints = control_proof_fingerprints(project_root)
    target = require_capability(load_capability_registry(project_root), CAPABILITY_ID)
    manifest = ProofManifest(
        schema_version=1,
        capability_id=CAPABILITY_ID,
        proof_id=report.proof_id,
        run_id=report.proof_id,
        data_class=DATA_CLASS_RAW,
        verdict="adopt",
        fingerprints=fingerprints,
        stages={"preflight": "validated"},
        validators={
            VALIDATOR_CHECKSUMS: "pass",
            VALIDATOR_STAGE: "pass",
            "stage:preflight": "pass",
        },
        artifacts=dict(report.artifact_checksums),
    )
    validate_proof_manifest(manifest.as_json_dict(), target, fingerprints)
    summary = proof_summary(manifest)
    manifest_payload = canonical_json(manifest.as_json_dict())
    raw = digest_bytes(manifest_payload)
    payloads = {
        "proof-manifest.json": manifest_payload.decode("utf-8"),
        "summary.txt": summary + "\n",
        FINGERPRINT_FILENAME: canonical_json(fingerprint_document(DATA_CLASS_RAW, raw)).decode(
            "utf-8"
        ),
        "scenario.json": canonical_json(_scenario_payload(report)).decode("utf-8"),
        "gates.json": canonical_json(gates).decode("utf-8"),
        "forecast-summary.json": canonical_json(
            {
                "confidence": report.forecast_confidence,
                "decision": report.forecast_decision,
            }
        ).decode("utf-8"),
    }
    refuse_proof_payloads(payloads)
    destination = published_proof_dir(results_dir, CAPABILITY_ID, report.proof_id)
    _claim_destination(destination)
    for name, text in payloads.items():
        (destination / name).write_text(text, encoding="utf-8")
    return ProofPublishResult(destination, destination / "proof-manifest.json", raw, summary)


def _scenario_payload(report: ControlScenarioReport) -> dict[str, object]:
    return {
        "archive_unmodified": report.source_before.fingerprint == report.source_after.fingerprint,
        "bump_alpha_invoked": report.bump_alpha_invoked,
        "deltas": {name: _delta_payload(item) for name, item in sorted(report.deltas.items())},
        "forecast_decision": report.forecast_decision,
        "invalidation_marked": report.invalidation_marked,
        "noop_worker_invocations": report.noop_worker_invocations,
        "prune_removed": report.prune_removed,
        "rebuild_match": report.rebuild_match,
        "resume_ok": report.resume_ok,
        "sole_recovery_blocked": report.sole_recovery_blocked,
        "space_refused": report.space_refused,
        "source_files": report.source_before.file_count,
    }


def _delta_payload(item: ShardDelta) -> dict[str, object]:
    return {
        "active_rows": item.active_rows,
        "cached": list(item.cached),
        "invoked": list(item.invoked),
        "kind": item.kind,
        "kinds": list(item.kinds),
        "last_occurrence": item.last_occurrence,
        "retracted": item.retracted,
        "tombstone_hashes": list(item.tombstone_hashes),
    }


def _claim_destination(destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink() or destination.exists():
        from arxiv_int.evaluation.evaluate.errors import ProofExistsError

        raise ProofExistsError(f"proof already exists: {destination}")
    try:
        destination.mkdir()
    except FileExistsError as error:
        from arxiv_int.evaluation.evaluate.errors import ProofExistsError

        raise ProofExistsError(f"proof already exists: {destination}") from error

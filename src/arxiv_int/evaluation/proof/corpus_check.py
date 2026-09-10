"""Read-only verification of corpus proofs and their referenced source artifacts."""

from pathlib import Path

from arxiv_int.evaluation.bundles import verify_run_bundle
from arxiv_int.evaluation.bundles.layout import digest_bytes
from arxiv_int.evaluation.bundles.manifest import canonical_json
from arxiv_int.evaluation.proof.checks import validate_proof_manifest
from arxiv_int.evaluation.proof.corpus_artifacts import STAGES, artifact_record, require
from arxiv_int.evaluation.proof.corpus_identity import corpus_fingerprints, resolve_reference
from arxiv_int.evaluation.proof.corpus_metrics import resource_summary
from arxiv_int.evaluation.proof.corpus_validate import validate_corpus
from arxiv_int.evaluation.proof.model import load_capability_registry, require_capability
from arxiv_int.pipeline.commands import require_frozen_context
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.run.persist import RunStatus, StageExecution, load_json
from arxiv_int.runtime import load_runtime_config

CAPABILITY = "corpus-foundation"


def check_corpus_proof(directory: Path, project_root: Path) -> str:
    """Verify the immutable bundle, current producers, external bytes and full corpus invariants."""
    verify_run_bundle(directory)
    payload = load_json(directory / "proof-manifest.json")
    config = load_runtime_config(project_root=project_root)
    context = require_frozen_context(config.runs_dir, payload["run_id"], project_root=project_root)
    fingerprints, producers = corpus_fingerprints(context, production_registry())
    target = require_capability(load_capability_registry(project_root), CAPABILITY)
    manifest = validate_proof_manifest(payload, target, fingerprints)
    require(
        manifest.capability_id == CAPABILITY and manifest.verdict == "passed",
        "invalid corpus verdict",
    )
    for name, record in manifest.artifacts.items():
        require(artifact_record(directory / name) == record, "proof payload checksum mismatch")
    for name, record in load_json(directory / "artifacts.json").items():
        require(
            artifact_record(resolve_reference(name, context)) == record,
            "external corpus artifact changed",
        )
    report = load_json(directory / "report.json")
    require(
        resource_summary((directory / "progress-first.jsonl").read_bytes()) == report["resources"],
        "resource evidence does not reproduce",
    )
    resource_summary((directory / "progress-replay.jsonl").read_bytes())
    for name in ("forecast-first.json", "forecast-replay.json"):
        require(
            load_json(directory / name)["decision"] in {"ready", "degraded"},
            "forecast did not pass",
        )
    require(report["producer_identities"] == producers, "recorded producer identities differ")
    require(
        len(report["replay"]) == len(STAGES) + 1
        and {row["stage"] for row in report["replay"]} == {"preflight", *STAGES},
        "replay stage coverage is incomplete",
    )
    require(
        all(row["reuse_key"] == producers[row["stage"]]["reuse_key"] for row in report["first"]),
        "recorded stage identity differs",
    )
    first = tuple(
        StageExecution(**{**row, "directory": str(resolve_reference(row["directory"], context))})
        for row in report["first"]
    )
    status = RunStatus(context.run_id, context.generation_id, False, "", first, (), ())
    _snapshots, metrics = validate_corpus(context, status)
    require(
        canonical_json(metrics) == canonical_json(report["metrics"]),
        "proof metrics no longer reproduce",
    )
    require(
        report["noop_worker_invocations"] == 0
        and all(row["cache_hit"] and not row["worker_invoked"] for row in report["replay"]),
        "invalid replay evidence",
    )
    digest = digest_bytes((directory / "proof-manifest.json").read_bytes())
    require(
        load_json(directory / "fingerprint.json")["raw_fingerprint"] == digest,
        "bundle fingerprint mismatch",
    )
    return digest

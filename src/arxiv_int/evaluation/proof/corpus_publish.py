"""Publish the validated corpus closure and its zero-worker unchanged replay."""

import logging
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from arxiv_int.evaluation.bundles import BundleSpec, publish_run_bundle
from arxiv_int.evaluation.bundles.layout import digest_bytes
from arxiv_int.evaluation.bundles.manifest import canonical_json
from arxiv_int.evaluation.evaluate.paths import published_proof_dir
from arxiv_int.evaluation.proof.checks import validate_proof_manifest
from arxiv_int.evaluation.proof.corpus_artifacts import (
    STAGES,
    artifact_record,
    require,
    snapshot_files,
)
from arxiv_int.evaluation.proof.corpus_identity import (
    corpus_fingerprints,
    reference,
)
from arxiv_int.evaluation.proof.corpus_metrics import resource_summary
from arxiv_int.evaluation.proof.corpus_validate import validate_corpus
from arxiv_int.evaluation.proof.model import (
    ProofManifest,
    load_capability_registry,
    require_capability,
)
from arxiv_int.evaluation.proof.ops import ProofPublishResult, fingerprint_document, proof_summary
from arxiv_int.pipeline.commands import require_frozen_context
from arxiv_int.pipeline.dag.actions import plan_for
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.forecast.commands import bind_forecast, forecast_or_refuse
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.locking import pipeline_lock
from arxiv_int.pipeline.run.persist import RunStatus, load_json, load_status
from arxiv_int.runtime import load_runtime_config

_LOG = logging.getLogger(__name__)
CAPABILITY = "corpus-foundation"


def publish_corpus_proof(
    *,
    project_root: Path,
    run_id: str,
    results_dir: Path,
    runs_dir: Path,
    proof_id: str | None = None,
) -> ProofPublishResult:
    """Validate an existing ordinary run, replay its corpus closure and seal all evidence."""
    context = require_frozen_context(runs_dir, run_id, project_root=project_root)
    require(context.results_dir == results_dir, "proof result root differs from frozen run")
    require(
        context.to_stage == "chunk" and context.from_stage is None,
        "corpus proof requires a complete closure ending at chunk",
    )
    destination = published_proof_dir(results_dir, CAPABILITY, proof_id or run_id)
    require(not destination.exists(), "corpus proof already exists")
    with pipeline_lock(runs_dir):
        return _publish(context, destination)


def _publish(context: RunContext, destination: Path) -> ProofPublishResult:
    registry = production_registry()
    fingerprints, producers = corpus_fingerprints(context, registry)
    first = load_status(context.runs_dir, context.run_id)
    for item in first.executions:
        if item.stage in producers:
            require(
                item.reuse_key == producers[item.stage]["reuse_key"],
                "producer changed since the corpus run; rerun the closure",
            )
    _LOG.info("validating corpus contracts, source bytes, accounting and offsets")
    snapshots, metrics = validate_corpus(context, first)
    progress = context.runs_dir / context.run_id / "logs/progress.jsonl"
    require(progress.is_file(), "missing corpus resource and timing evidence")
    progress_first = progress.read_bytes()
    resources = resource_summary(progress_first)
    initial_forecast = load_json(context.runs_dir / context.run_id / "forecast/decision.json")
    require(initial_forecast["decision"] in {"ready", "degraded"}, "initial forecast did not pass")
    config = load_runtime_config(project_root=context.project_root)
    forecast_or_refuse(context, config, registry)
    plan = plan_for(registry, context)
    _document, guard = bind_forecast(context, registry, plan, config)
    started = time.monotonic()
    _LOG.info("replaying unchanged corpus closure")
    replay = Orchestrator(registry, context.runs_dir, space_guard=guard).execute_plan(context, plan)
    seconds = time.monotonic() - started
    require(
        not replay.halted and {item.stage for item in replay.executions} == {"preflight", *STAGES},
        "replay did not complete corpus closure",
    )
    require(
        all(item.cache_hit and not item.worker_invoked for item in replay.executions),
        "unchanged replay invoked a worker",
    )
    require_frozen_context(context.runs_dir, context.run_id, project_root=context.project_root)
    current, _ = corpus_fingerprints(context, production_registry())
    require(current == fingerprints, "producer or model changed during proof")
    artifacts = _artifact_registry(context, first, snapshots)
    report = {
        "metrics": metrics,
        "resources": resources,
        "replay_seconds": seconds,
        "noop_worker_invocations": 0,
        "first": _status(first, context),
        "replay": _status(replay, context),
        "producer_identities": producers,
        "source_condition": "read-only access; metadata bracket and post-run physical content hashes matched",
        "source_limit": "changes reverted between observations remain undetectable",
    }
    payloads = {
        "progress-first.jsonl": progress_first,
        "progress-replay.jsonl": progress.read_bytes(),
        "report.json": canonical_json(report),
        "artifacts.json": canonical_json(artifacts),
        "forecast-first.json": _redacted(initial_forecast, context),
        "forecast-replay.json": _redacted(
            load_json(context.runs_dir / context.run_id / "forecast/decision.json"), context
        ),
    }
    return _seal(context, destination, fingerprints, first, payloads)


def _artifact_registry(
    context: RunContext, first: RunStatus, snapshots: dict[str, tuple[Path, dict[str, Any]]]
) -> dict[str, dict[str, int | str]]:
    paths: set[Path] = set()
    for path, summary in snapshots.values():
        paths.update(snapshot_files(path, summary))
    for item in first.executions:
        directory = Path(item.directory or "")
        paths.update(directory / name for name in ("manifest.json", "stage.json", "quality.json"))
    return {reference(path, context): artifact_record(path) for path in sorted(paths)}


def _status(status: RunStatus, context: RunContext) -> list[dict[str, Any]]:
    result = []
    for item in status.executions:
        row = asdict(item)
        row["directory"] = reference(Path(item.directory or ""), context)
        result.append(row)
    return result


def _redacted(value: Any, context: RunContext) -> bytes:
    text = canonical_json(value).decode("ascii")
    roots = {**dict(context.secret_free), "PROJECT_ROOT": str(context.project_root)}
    for name, root in sorted(roots.items(), key=lambda item: len(item[1]), reverse=True):
        if root.startswith("/"):
            text = text.replace(root, f"${name}")
    return text.encode("ascii")


def _seal(
    context: RunContext,
    destination: Path,
    fingerprints: dict[str, str],
    first: RunStatus,
    payloads: dict[str, bytes],
) -> ProofPublishResult:
    manifest = ProofManifest(
        1,
        CAPABILITY,
        destination.name,
        context.run_id,
        "raw",
        "passed",
        fingerprints,
        {
            item.stage: "empty" if item.outcome == "empty" else "validated"
            for item in first.executions
            if item.stage in STAGES
        },
        {
            "artifact-checksums": "pass",
            "stage-validation": "pass",
            **{f"stage:{stage}": "pass" for stage in STAGES},
        },
        {
            name: {"bytes": len(data), "sha256": digest_bytes(data)}
            for name, data in payloads.items()
        },
    )
    target = require_capability(load_capability_registry(context.project_root), CAPABILITY)
    validate_proof_manifest(manifest.as_json_dict(), target, fingerprints)
    payloads["proof-manifest.json"] = canonical_json(manifest.as_json_dict())
    fingerprint = digest_bytes(payloads["proof-manifest.json"])
    payloads["fingerprint.json"] = canonical_json(fingerprint_document("raw", fingerprint))
    summary = proof_summary(manifest)
    payloads["summary.txt"] = (summary + "\n").encode("ascii")
    publish_run_bundle(
        destination,
        BundleSpec(
            destination.name,
            CAPABILITY,
            fingerprints,
            {
                "command": "make pipeline TO=chunk; make proof CAPABILITY=corpus-foundation RUN_ID=<run-id>"
            },
            {},
            "passed",
        ),
        (),
        artifacts=payloads,
    )
    return ProofPublishResult(
        destination, destination / "proof-manifest.json", fingerprint, summary
    )

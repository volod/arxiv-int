"""Run forecast, resume, cache-hit, delta, invalidation, rebuild, and prune drills."""

import hashlib
import logging
from pathlib import Path

from arxiv_int.evaluation.evaluate.errors import ProofIntegrityError
from arxiv_int.evaluation.proof.control_copy import ProofWorkspace, snapshot_sources
from arxiv_int.evaluation.proof.control_deltas import run_source_deltas, stage_shards
from arxiv_int.evaluation.proof.control_model import ControlScenarioReport
from arxiv_int.evaluation.proof.control_registry import (
    CONTROL_OPTIONAL,
    CONTROL_PROFILE_STAGES,
    control_proof_registry,
)
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.dag.actions import (
    fixture_plan,
    persist_new_context,
    rebuild_context,
    remaining_plan,
    update_context,
)
from arxiv_int.pipeline.dag.graph import StagePlan
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.registry import StageRegistry
from arxiv_int.pipeline.forecast.commands import bind_forecast, forecast_or_refuse
from arxiv_int.pipeline.forecast.errors import ForecastRefusedError
from arxiv_int.pipeline.forecast.persist import load_forecast
from arxiv_int.pipeline.forecast.recheck import recheck_free_space
from arxiv_int.pipeline.prune.apply import apply_prune_plan
from arxiv_int.pipeline.prune.plan import build_prune_plan
from arxiv_int.pipeline.reconcile.commands import prepare_update, record_rebuild
from arxiv_int.pipeline.run.context import (
    RunContext,
    allocate_run_id,
    config_fingerprint,
    secret_free_values,
    snapshot_silos,
)
from arxiv_int.pipeline.run.fixtures import FixtureStage
from arxiv_int.pipeline.run.persist import RunStatus, save_context
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.filesystem import FilesystemEvidence

_LOG = logging.getLogger(__name__)


def run_control_scenario(
    workspace: ProofWorkspace,
    project_root: Path,
    proof_id: str,
    sources: tuple[SiloRoot, ...],
) -> ControlScenarioReport:
    """Exercise then-usable control stages on the disposable copy."""
    registry, runners = control_proof_registry()
    plan = _plan(registry)
    config = workspace.config
    context = _make_context(workspace, project_root)
    first = _resume_first_generation(context, config, registry, plan, runners)
    resume_ok = True
    checksums = _preflight_checksums(first)
    forecast = load_forecast(context.runs_dir, context.run_id)
    sole_recovery = _probe_sole_recovery(workspace, project_root)
    noop = _walk(context, config, registry, plan)
    noop_workers = sum(1 for item in noop.executions if item.worker_invoked)
    latest, deltas = run_source_deltas(context, config, registry, plan, _walk)
    marked = Orchestrator(registry, latest.runs_dir).invalidate("alpha")
    bumped_registry, _runners = control_proof_registry(alpha_version="2")
    bumped_plan = _plan(bumped_registry)
    bumped = persist_new_context(update_context(latest))
    prepare_update(latest, bumped, Orchestrator(bumped_registry, bumped.runs_dir))
    bump_status = _walk(bumped, config, bumped_registry, bumped_plan)
    space_refused = _simulate_low_space(bumped, config, bumped_registry)
    rebuilt = persist_new_context(rebuild_context(bumped))
    _walk(rebuilt, config, bumped_registry, bumped_plan, force=True)
    rebuild = record_rebuild(bumped, rebuilt)
    extra = persist_new_context(rebuild_context(rebuilt))
    _walk(extra, config, bumped_registry, bumped_plan, force=True)
    prune_plan = build_prune_plan(extra.runs_dir)
    removed = 0
    if prune_plan.eligible:
        removed = apply_prune_plan(extra.runs_dir, prune_plan.plan_id)
    after = snapshot_sources(sources)
    invoked, _cached = stage_shards(bump_status, "alpha")
    preflight_hits = sum(
        1 for item in bump_status.executions if item.stage == "preflight" and item.cache_hit
    )
    _LOG.info("control proof scenario complete proof_id=%s", proof_id)
    return ControlScenarioReport(
        proof_id,
        forecast.decision,
        forecast.confidence,
        resume_ok,
        noop_workers,
        deltas,
        len(marked),
        len(invoked),
        preflight_hits,
        space_refused,
        rebuild.baseline_match,
        sole_recovery,
        removed,
        len(prune_plan.eligible),
        workspace.source_before,
        after,
        bool(checksums),
        checksums,
    )


def _plan(registry: StageRegistry) -> StagePlan:
    return fixture_plan(
        registry,
        profile_stages=CONTROL_PROFILE_STAGES,
        optional_stages=CONTROL_OPTIONAL,
    )


def _make_context(workspace: ProofWorkspace, project_root: Path) -> RunContext:
    secret = secret_free_values(dict(workspace.config.values))
    run_id = allocate_run_id()
    context = RunContext(
        run_id,
        run_id,
        "fixture",
        config_fingerprint("fixture", secret),
        snapshot_silos(workspace.silos),
        workspace.silos,
        workspace.config.results_dir,
        workspace.config.runs_dir,
        project_root,
        secret,
        {},
    )
    save_context(context)
    return context


def _walk(
    context: RunContext,
    config: RuntimeConfig,
    registry: StageRegistry,
    plan: StagePlan,
    *,
    force: bool = False,
) -> RunStatus:
    forecast_or_refuse(context, config, registry, force=force)
    _document, guard = bind_forecast(context, registry, plan, config, force=force)
    status = Orchestrator(registry, context.runs_dir, space_guard=guard).execute_plan(
        context, plan, force=force
    )
    if status.halted:
        raise ProofIntegrityError(status.halt_reason or "control proof DAG halted")
    return status


def _resume_first_generation(
    context: RunContext,
    config: RuntimeConfig,
    registry: StageRegistry,
    plan: StagePlan,
    runners: dict[str, FixtureStage],
) -> RunStatus:
    partial = fixture_plan(
        registry,
        profile_stages=CONTROL_PROFILE_STAGES,
        optional_stages=CONTROL_OPTIONAL,
        to_stage="alpha",
    )
    first = _walk(context, config, registry, partial)
    alpha_calls = runners["alpha"].calls
    remaining = remaining_plan(plan, first)
    resumed = _walk(context, config, registry, remaining)
    if runners["alpha"].calls != alpha_calls:
        raise ProofIntegrityError("resume replayed the completed alpha worker")
    return RunStatus(
        first.run_id,
        first.generation_id,
        resumed.halted,
        resumed.halt_reason,
        first.executions + resumed.executions,
        first.lineage + resumed.lineage,
        resumed.not_selected,
    )


def _probe_sole_recovery(workspace: ProofWorkspace, project_root: Path) -> bool:
    registry, _runners = control_proof_registry()
    plan = _plan(registry)
    runs = workspace.work_root / "sole-runs"
    results = workspace.work_root / "sole-results"
    runs.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    secret = secret_free_values(dict(workspace.config.values))
    run_id = allocate_run_id()
    context = RunContext(
        run_id,
        run_id,
        "fixture",
        config_fingerprint("fixture", secret),
        snapshot_silos(workspace.silos),
        workspace.silos,
        results,
        runs,
        project_root,
        secret,
        {},
    )
    save_context(context)
    _walk(context, workspace.config, registry, plan)
    Orchestrator(registry, runs).invalidate("preflight")
    prune_plan = build_prune_plan(runs)
    return any(item.kind == "sole-recovery" for item in prune_plan.blocked)


def _simulate_low_space(
    context: RunContext, config: RuntimeConfig, registry: StageRegistry
) -> bool:
    document = forecast_or_refuse(context, config, registry)

    def inspector(path: Path) -> FilesystemEvidence:
        return FilesystemEvidence(path, "ext4", "8:1", False, 0, True, False)

    try:
        recheck_free_space(document, inspector, "alpha")
    except ForecastRefusedError:
        return True
    return False


def _preflight_checksums(status: RunStatus) -> dict[str, dict[str, int | str]]:
    artifacts: dict[str, dict[str, int | str]] = {}
    for item in status.executions:
        path = Path(item.directory or "") / "stage.json"
        if item.stage != "preflight" or not path.is_file():
            continue
        artifacts[f"preflight/{item.shard_id}/stage.json"] = {
            "bytes": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    if not artifacts:
        raise ProofIntegrityError("preflight produced no checksummed artifacts")
    return artifacts

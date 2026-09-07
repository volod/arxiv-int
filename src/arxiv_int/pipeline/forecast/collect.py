"""Gather inventory, cache, telemetry, and filesystem evidence for one forecast."""

from collections.abc import Callable
from pathlib import Path

from arxiv_int.inference.resources import HostSnapshot, snapshot_host
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.actions import plan_for
from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.forecast.capacity import envelope_fingerprint, load_envelope
from arxiv_int.pipeline.forecast.devices import Inspector, collect_devices
from arxiv_int.pipeline.forecast.evidence import cache_plan, load_comparable_runs
from arxiv_int.pipeline.forecast.inputs import ForecastInputs
from arxiv_int.pipeline.forecast.model import HostAssumptions
from arxiv_int.pipeline.forecast.persist import allocate_forecast_id
from arxiv_int.pipeline.forecast.sample import resolve_inventory
from arxiv_int.pipeline.graph import StagePlan
from arxiv_int.pipeline.persist import run_dir
from arxiv_int.pipeline.registry import ResourceEstimate, StageRegistry
from arxiv_int.runtime.config_model import RuntimeConfig

HostProbe = Callable[[], HostSnapshot]


def collect_inputs(
    context: RunContext,
    registry: StageRegistry,
    config: RuntimeConfig,
    *,
    forecast_id: str | None = None,
    production: bool = True,
    inspector: Inspector | None = None,
    host_probe: HostProbe | None = None,
    envelope_root: Path | None = None,
    from_stage: str | None = None,
    to_stage: str | None = None,
) -> tuple[ForecastInputs, StagePlan]:
    """Read-only collection; never loads models or writes artifacts."""
    envelope = load_envelope(envelope_root or context.project_root)
    plan = plan_for(
        registry,
        context,
        from_stage=from_stage if from_stage is not None else context.from_stage,
        to_stage=to_stage if to_stage is not None else context.to_stage,
    )
    inventory = resolve_inventory(
        context.silos,
        (run_dir(context.runs_dir, context.run_id), context.runs_dir),
        file_limit=envelope.sample_file_limit,
    )
    cache = cache_plan(context, registry, plan.execute)
    comparable = load_comparable_runs(
        context.runs_dir, profile=context.profile, current_id=context.run_id
    )
    devices = collect_devices(config, inspector)
    host = _host_assumptions(context, host_probe)
    chosen = forecast_id or context.run_id or allocate_forecast_id()
    estimates = {spec.name: spec.resource_estimate for spec in registry.specs()}
    gpu_stages = frozenset(
        spec.name for spec in registry.specs() if spec.resource_estimate.gpu_required
    )
    inputs = ForecastInputs(
        forecast_id=chosen,
        run_id=context.run_id if production else None,
        production=production,
        profile=context.profile,
        plan=plan.execute,
        not_selected=plan.not_selected,
        config_fingerprint=context.config_fingerprint,
        source_snapshot=context.source_snapshot,
        envelope=envelope,
        envelope_fingerprint=envelope_fingerprint(envelope),
        inventory=inventory,
        cache=cache,
        comparable=comparable,
        devices=devices,
        host=host,
        estimates=estimates,
        gpu_stages=gpu_stages,
    )
    return inputs, plan


def estimates_for(registry: StageRegistry) -> dict[str, ResourceEstimate]:
    """Return declared envelopes keyed by stage name."""
    return {spec.name: spec.resource_estimate for spec in registry.specs()}


def _host_assumptions(context: RunContext, host_probe: HostProbe | None) -> HostAssumptions:
    snapshot = (host_probe or snapshot_host)()
    workers = 1
    raw = context.secret_free.get("PIPELINE_WORKERS", "")
    if raw.isdigit() and int(raw) > 0:
        workers = int(raw)
    return HostAssumptions(
        ram_available_gib=snapshot.available_ram_gib,
        gpu_name=snapshot.gpu_name,
        gpu_total_gib=snapshot.total_gpu_gib,
        device_id=snapshot.device_id,
        workers=workers,
    )


def silos_from_config(config: RuntimeConfig) -> tuple[SiloRoot, ...]:
    """Map configured archive silos into pipeline silo roots."""
    return tuple(SiloRoot(silo.silo_id, silo.root) for silo in config.archive_silos)

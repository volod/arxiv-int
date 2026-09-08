"""CLI and orchestrator handlers for the read-only forecast command."""

import logging
from collections.abc import Callable
from pathlib import Path

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.dag.graph import StagePlan
from arxiv_int.pipeline.dag.registry import StageRegistry
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.forecast.collect import collect_inputs, silos_from_config
from arxiv_int.pipeline.forecast.devices import Inspector
from arxiv_int.pipeline.forecast.engine import build_forecast
from arxiv_int.pipeline.forecast.errors import EXIT_RESOURCE, ForecastRefusedError
from arxiv_int.pipeline.forecast.model import ForecastDocument
from arxiv_int.pipeline.forecast.persist import (
    allocate_forecast_id,
    require_fresh_forecast,
    save_forecast,
)
from arxiv_int.pipeline.forecast.recheck import make_space_guard
from arxiv_int.pipeline.forecast.report import console_lines
from arxiv_int.pipeline.run.context import RunContext, config_fingerprint, secret_free_values
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.config_model import RuntimeConfig

_LOG = logging.getLogger(__name__)


def run_forecast_command(args: object, *, inspector: Inspector | None = None) -> int:
    """Dispatch ``arxiv-int pipeline forecast`` for a frozen run or standalone archive."""
    run_id = getattr(args, "run_id", None)
    project_root = getattr(args, "project_root", None)
    if run_id:
        from arxiv_int.pipeline.commands import require_frozen_context

        config = load_runtime_config(project_root=project_root)
        context = require_frozen_context(
            config.runs_dir,
            str(run_id),
            project_root=project_root,
            archive_dir=getattr(args, "archive_dir", None),
            results_dir=getattr(args, "results_dir", None),
        )
        document = forecast_bound_run(
            context,
            config,
            production_registry(),
            inspector=inspector,
            force=bool(getattr(args, "force", False)),
        )
        return _emit(document, config.runs_dir)
    config = _load_config(args)
    document = forecast_standalone(
        config,
        production_registry(),
        from_stage=getattr(args, "from_stage", None),
        to_stage=getattr(args, "to_stage", None),
        inspector=inspector,
        force=bool(getattr(args, "force", False)),
    )
    return _emit(document, config.runs_dir)


def forecast_bound_run(
    context: RunContext,
    config: RuntimeConfig,
    registry: StageRegistry,
    *,
    inspector: Inspector | None = None,
    force: bool = False,
) -> ForecastDocument:
    """Forecast using a created run's frozen inputs; retain the JSON under that run."""
    inputs, _plan = collect_inputs(
        context,
        registry,
        config,
        forecast_id=context.run_id,
        production=True,
        inspector=inspector,
        force=force,
    )
    document = build_forecast(inputs)
    save_forecast(context.runs_dir, document)
    return document


def forecast_standalone(
    config: RuntimeConfig,
    registry: StageRegistry,
    *,
    from_stage: str | None = None,
    to_stage: str | None = None,
    inspector: Inspector | None = None,
    force: bool = False,
) -> ForecastDocument:
    """Forecast without allocating a production generation."""
    forecast_id = allocate_forecast_id()
    context = _ephemeral_context(config, forecast_id, from_stage, to_stage)
    inputs, _plan = collect_inputs(
        context,
        registry,
        config,
        forecast_id=forecast_id,
        production=False,
        force=force,
        inspector=inspector,
    )
    document = build_forecast(inputs)
    save_forecast(config.runs_dir, document)
    return document


def forecast_or_refuse(
    context: RunContext,
    config: RuntimeConfig,
    registry: StageRegistry,
    *,
    inspector: Inspector | None = None,
    force: bool = False,
) -> ForecastDocument:
    """Write a fresh forecast and refuse blocked work before heavy stages."""
    document = forecast_bound_run(context, config, registry, inspector=inspector, force=force)
    if document.decision == "blocked":
        raise ForecastRefusedError(_blocked_message(document))
    return document


def bind_forecast(
    context: RunContext,
    registry: StageRegistry,
    plan: StagePlan,
    config: RuntimeConfig,
    *,
    inspector: Inspector | None = None,
    force: bool = False,
) -> tuple[ForecastDocument, Callable[[str], None]]:
    """Require a fresh covering forecast and return a stage-boundary space guard."""
    inputs, _plan = collect_inputs(context, registry, config, inspector=inspector, force=force)
    document = require_fresh_forecast(context, plan, inputs)
    if document.decision == "blocked":
        raise ForecastRefusedError(_blocked_message(document))
    return document, make_space_guard(document, inspector)


def _emit(document: ForecastDocument, runs_dir: Path) -> int:
    for line in console_lines(document):
        _LOG.info("%s", line)
    _LOG.info("json=%s", runs_dir / document.forecast_id / "forecast" / "decision.json")
    if document.decision == "blocked":
        return EXIT_RESOURCE
    return 0


def _blocked_message(document: ForecastDocument) -> str:
    detail = "; ".join(document.actions) or document.decision
    return f"forecast blocked ({document.forecast_id}): {detail}"


def _ephemeral_context(
    config: RuntimeConfig,
    forecast_id: str,
    from_stage: str | None,
    to_stage: str | None,
) -> RunContext:
    from arxiv_int.runtime.setup.settings import load_setup_settings

    settings = load_setup_settings(project_root=config.project_root)
    silos = silos_from_config(config)
    secret_free = secret_free_values(dict(config.values))
    profile = settings.pipeline_profile
    roots = [{"silo_id": silo.silo_id, "root": str(silo.root)} for silo in silos]
    return RunContext(
        run_id=forecast_id,
        generation_id=forecast_id,
        profile=profile,
        config_fingerprint=config_fingerprint(profile, secret_free),
        source_snapshot=sha256_text(normalize_json({"silos": roots})),
        silos=silos,
        results_dir=config.results_dir,
        runs_dir=config.runs_dir,
        project_root=config.project_root,
        secret_free=secret_free,
        parameters={},
        from_stage=from_stage,
        to_stage=to_stage,
    )


def _load_config(args: object) -> RuntimeConfig:
    cli: dict[str, str | None] = {}
    archive_dir = getattr(args, "archive_dir", None)
    results_dir = getattr(args, "results_dir", None)
    if archive_dir is not None:
        cli["ARCHIVE_DIR"] = str(archive_dir)
    if results_dir is not None:
        cli["RESULTS_DIR"] = str(results_dir)
    return load_runtime_config(project_root=getattr(args, "project_root", None), cli=cli)

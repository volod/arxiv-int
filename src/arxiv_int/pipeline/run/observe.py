"""Build a stage observability session for one orchestrator step."""

from collections.abc import Callable

from arxiv_int.observability.logging.redact import extra_secrets_from_env, shard_token
from arxiv_int.observability.logging.session import StageSession
from arxiv_int.observability.metrics.constants import (
    DEFAULT_LOG_FORMAT,
    DEFAULT_PROGRESS_INTERVAL_SEC,
    LOG_FORMATS,
)
from arxiv_int.observability.metrics.resources import ResourceProbe
from arxiv_int.observability.sinks import ProgressStore
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import run_dir

_CLOCK = Callable[[], float]


def _log_format(context: RunContext) -> str:
    value = context.secret_free.get("LOG_FORMAT", DEFAULT_LOG_FORMAT)
    return value if value in LOG_FORMATS else DEFAULT_LOG_FORMAT


def _interval_sec(context: RunContext, override: float | None) -> float:
    if override is not None:
        return override
    raw = context.secret_free.get("PROGRESS_INTERVAL_SEC", "")
    try:
        interval = float(raw) if raw else DEFAULT_PROGRESS_INTERVAL_SEC
    except ValueError:
        return DEFAULT_PROGRESS_INTERVAL_SEC
    return interval if interval > 0 else DEFAULT_PROGRESS_INTERVAL_SEC


def open_stage_session(
    context: RunContext,
    stage: str,
    *,
    sampler: ResourceProbe | None = None,
    store: ProgressStore | None = None,
    clock: _CLOCK | None = None,
    interval_sec: float | None = None,
    extra_secrets: tuple[str, ...] = (),
    background_heartbeats: bool = True,
) -> StageSession:
    """Bind logs and progress files under ``$RUNS_DIR/<run-id>/``."""
    directory = run_dir(context.runs_dir, context.run_id)
    directory.mkdir(parents=True, exist_ok=True)
    secrets = extra_secrets or extra_secrets_from_env()
    return StageSession(
        directory,
        context.run_id,
        stage,
        shard=shard_token(context.parameters.get("document_id", "default")),
        sampler=sampler,
        store=store,
        clock=clock,
        interval_sec=_interval_sec(context, interval_sec),
        log_format=_log_format(context),
        extra_secrets=secrets,
        background_heartbeats=background_heartbeats,
    )

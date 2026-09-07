"""Read and write fingerprinted forecast decisions under RUNS_DIR."""

from pathlib import Path
from uuid import uuid4

from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.forecast.codec import document_payload
from arxiv_int.pipeline.forecast.errors import StaleForecastError
from arxiv_int.pipeline.forecast.inputs import ForecastInputs
from arxiv_int.pipeline.forecast.model import ForecastDocument
from arxiv_int.pipeline.graph import StagePlan
from arxiv_int.pipeline.persist import load_json, run_dir, write_json

FORECAST_DIR = "forecast"
DECISION_NAME = "decision.json"


def allocate_forecast_id() -> str:
    """Return a standalone forecast id that is not a production generation."""
    return f"forecast-{uuid4().hex}"


def forecast_dir(runs_dir: Path, forecast_id: str) -> Path:
    """Return ``$RUNS_DIR/<id>/forecast/``."""
    return run_dir(runs_dir, forecast_id) / FORECAST_DIR


def save_forecast(runs_dir: Path, document: ForecastDocument) -> Path:
    """Atomically write ``decision.json`` for a run or standalone forecast id."""
    path = forecast_dir(runs_dir, document.forecast_id) / DECISION_NAME
    write_json(path, document_payload(document))
    return path


def load_forecast(runs_dir: Path, forecast_id: str) -> ForecastDocument:
    """Load a previously written decision; used for freshness checks."""
    from arxiv_int.pipeline.forecast.decode import document_from_payload

    payload = load_json(forecast_dir(runs_dir, forecast_id) / DECISION_NAME)
    return document_from_payload(payload)


def require_fresh_forecast(
    context: RunContext,
    plan: StagePlan,
    inputs: ForecastInputs,
) -> ForecastDocument:
    """Refuse a missing, uncovered, or input-stale forecast."""
    path = forecast_dir(context.runs_dir, context.run_id) / DECISION_NAME
    if not path.is_file():
        raise StaleForecastError(
            f"run {context.run_id} has no forecast; run arxiv-int pipeline forecast --run-id "
            f"{context.run_id}"
        )
    document = load_forecast(context.runs_dir, context.run_id)
    covered = set(document.plan)
    requested = set(plan.execute)
    if document.config_fingerprint != context.config_fingerprint:
        raise StaleForecastError(f"run {context.run_id} forecast is stale; configuration changed")
    if document.source_snapshot != context.source_snapshot:
        raise StaleForecastError(
            f"run {context.run_id} forecast is stale; archive snapshot changed"
        )
    if document.envelope_fingerprint != inputs.envelope_fingerprint:
        raise StaleForecastError(
            f"run {context.run_id} forecast is stale; capacity envelope changed"
        )
    if not requested <= covered:
        missing = ", ".join(sorted(requested - covered))
        raise StaleForecastError(
            f"run {context.run_id} forecast does not cover stage(s): {missing}"
        )
    stored_hits = {item.stage: item.cache_hit for item in document.stages}
    for name in plan.execute:
        if stored_hits.get(name) != inputs.cache.hit(name):
            raise StaleForecastError(
                f"run {context.run_id} forecast is stale; cache plan for {name} changed"
            )
    return document

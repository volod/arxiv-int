"""Run and cross-check ordinary lexical load and query on the configured archive."""

import os
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import create_engine

from arxiv_int.pipeline.commands import create_run_context, require_frozen_context, run_dag
from arxiv_int.pipeline.dag.actions import plan_for
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.forecast.commands import forecast_or_refuse
from arxiv_int.pipeline.inventory.snapshot import inventory_snapshot
from arxiv_int.pipeline.run.persist import RunStatus, load_status
from arxiv_int.retrieval.projection import active_target
from arxiv_int.retrieval.query_normalization import query_policy_fingerprint
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.project_root import find_project_root
from arxiv_int.stores.postgres.selection import store_database_url
from tests.integration.corpus.artifacts import require
from tests.integration.lexical.artifacts import (
    STAGE,
    live_reconciliation,
    validate_lexical_execution,
    write_integration_log,
)
from tests.integration.lexical.queries import prove_queries

pytestmark = [
    pytest.mark.archive,
    pytest.mark.skipif(not os.environ.get("ARCHIVE_DIR"), reason="ARCHIVE_DIR is not configured"),
]


def test_provided_archive_lexical_load_query_and_noop_replay() -> None:
    """Validate forecast, load, reconciliation, queries, citations, and cache reuse."""
    project_root = find_project_root()
    config = load_runtime_config(project_root=project_root)
    registry = production_registry()
    context = create_run_context(project_root=project_root, to_stage=STAGE)
    forecast = forecast_or_refuse(context, config, registry)
    require(forecast.decision != "blocked", "forecast refused the lexical load")
    code = run_dag(context, registry)
    first = load_status(context.runs_dir, context.run_id)
    require(code == 0, f"lexical dag failed: {first.halt_reason}")
    metrics = _validate_run(
        first, project_root, config.data_dir, forecast.decision, first_pass=True
    )
    require(metrics["canonicalChunks"] > 0, "configured archive produced an empty projection")
    require(
        inventory_snapshot(context.silos) == context.source_snapshot,
        "archive source-set changed during the lexical run",
    )

    plan = plan_for(registry, context)
    replay = Orchestrator(registry, context.runs_dir).execute_plan(context, plan)
    require(not replay.halted, "unchanged replay halted")
    require(
        all(item.cache_hit and not item.worker_invoked for item in replay.executions),
        "unchanged replay invoked a lexical or corpus worker",
    )
    require_frozen_context(context.runs_dir, context.run_id, project_root=project_root)
    replay_metrics = _validate_run(
        replay, project_root, config.data_dir, forecast.decision, first_pass=False
    )
    assert replay_metrics["canonicalChunks"] == metrics["canonicalChunks"]
    assert replay_metrics["manifestSha256"] == metrics["manifestSha256"]


def _validate_run(
    status: RunStatus,
    project_root: Path,
    data_dir: Path,
    forecast_decision: str,
    *,
    first_pass: bool,
) -> dict[str, Any]:
    require(not status.halted, "lexical run halted")
    lexical = next(item for item in status.executions if item.stage == STAGE)
    published = validate_lexical_execution(lexical)
    url = store_database_url(project_root)
    engine = create_engine(url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            target = active_target(connection)
            reconciliation = live_reconciliation(connection, target, published["summary"])
            query = prove_queries(connection, target)
    finally:
        engine.dispose()
    payload = {
        "activated": True,
        "cacheHit": lexical.cache_hit,
        "canonicalChunks": reconciliation.canonical_chunks,
        "canonicalDocuments": reconciliation.canonical_documents,
        "forecastDecision": forecast_decision,
        "manifestSha256": published["digest"],
        "projectionRows": reconciliation.projection_rows,
        "queryPolicyFingerprint": query_policy_fingerprint(),
        "runId": status.run_id,
        "tokenizerFingerprint": published["summary"]["index"]["tokenizer_fingerprint"],
        "unindexedChunks": reconciliation.unindexed_chunks,
        "workerInvoked": lexical.worker_invoked,
        **query,
    }
    if first_pass:
        write_integration_log(data_dir, payload)
    return payload

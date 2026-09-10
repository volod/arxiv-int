"""Run and cross-check the ordinary corpus pipeline on the configured archive."""

import os
from typing import Any

import pytest

from arxiv_int.pipeline.commands import create_run_context, require_frozen_context, run_dag
from arxiv_int.pipeline.dag.actions import plan_for
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.forecast.commands import forecast_or_refuse
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import RunStatus, load_status
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.project_root import find_project_root
from tests.integration.corpus.accounting import (
    account_duplicates,
    account_extraction,
    account_normalization,
    check_sources,
)
from tests.integration.corpus.artifacts import STAGES, require, validate_execution
from tests.integration.corpus.offsets import check_chunks, check_spans, check_views

pytestmark = [
    pytest.mark.archive,
    pytest.mark.skipif(not os.environ.get("ARCHIVE_DIR"), reason="ARCHIVE_DIR is not configured"),
]


def _validate_corpus(context: RunContext, status: RunStatus) -> dict[str, Any]:
    require(not status.halted, "corpus run halted")
    observed = [item for item in status.executions if item.stage in STAGES]
    require(len(observed) == len(STAGES), "expected exactly one execution per corpus stage")
    selected = {item.stage: item for item in observed}
    require(set(selected) == set(STAGES), "corpus run is missing a required stage")
    snapshots = {name: validate_execution(selected[name], context.project_root) for name in STAGES}
    inventory = check_sources(snapshots["inventory"][0], context)
    extraction = snapshots["extract"][1]
    normalization = snapshots["normalize"][1]
    documents, accounting = account_extraction(inventory, extraction)
    spans = check_spans(documents, extraction, inventory)
    normalized = account_normalization(documents, normalization)
    check_views(normalized, extraction, normalization)
    suppressed, duplicates = account_duplicates(normalized, snapshots["dedupe"][1])
    chunks = check_chunks(normalized, documents, suppressed, snapshots["chunk"][1], normalization)
    return {
        "accounting": accounting,
        "chunks": chunks,
        "duplicates": duplicates,
        "normalized_documents": len(normalized),
        "spans": spans,
    }


def test_provided_archive_pipeline_integrity_and_noop_replay() -> None:
    """Validate ordinary outputs, source bytes, cross-stage meaning, and cache reuse."""
    project_root = find_project_root()
    config = load_runtime_config(project_root=project_root)
    context = create_run_context(project_root=project_root, to_stage="chunk")
    registry = production_registry()
    forecast_or_refuse(context, config, registry)
    assert run_dag(context, registry) == 0

    first = load_status(context.runs_dir, context.run_id)
    first_metrics = _validate_corpus(context, first)
    require(first_metrics["accounting"]["occurrences"] > 0, "configured archive is empty")

    plan = plan_for(registry, context)
    replay = Orchestrator(registry, context.runs_dir).execute_plan(context, plan)
    require(not replay.halted, "unchanged replay halted")
    require(
        all(item.cache_hit and not item.worker_invoked for item in replay.executions),
        "unchanged replay invoked a corpus worker",
    )
    require_frozen_context(context.runs_dir, context.run_id, project_root=project_root)
    assert _validate_corpus(context, replay) == first_metrics

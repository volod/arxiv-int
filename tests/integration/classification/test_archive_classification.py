"""Forecast, execute and validate classification against the configured supplied archive."""

import logging
import os
from typing import Any

import pytest

from arxiv_int.classification.layout import ClassificationLayout
from arxiv_int.classification.policy import load_classifier_policy
from arxiv_int.pipeline.commands import create_run_context, require_frozen_context, run_dag
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.forecast.commands import forecast_or_refuse
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import load_json, load_status, write_json
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.project_root import find_project_root
from tests.integration.classification.artifacts import validate_classification_run
from tests.integration.classification.evidence import check_evidence
from tests.integration.classification.mapping import check_mapping
from tests.integration.classification.review import check_calibration, update_review
from tests.integration.corpus.accounting import (
    account_extraction,
    account_normalization,
    check_sources,
)
from tests.integration.corpus.artifacts import require
from tests.integration.corpus.offsets import check_spans, check_views

_LOG = logging.getLogger(__name__)
pytestmark = [
    pytest.mark.archive,
    pytest.mark.skipif(not os.environ.get("ARCHIVE_DIR"), reason="ARCHIVE_DIR is not configured"),
]


def _cross_check(context: RunContext) -> dict[str, Any]:
    status = load_status(context.runs_dir, context.run_id)
    summary, snapshots = validate_classification_run(context, status)
    inventory_path = snapshots["inventory"][0]
    inventory = check_sources(inventory_path, context)
    extraction, normalization = snapshots["extract"][1], snapshots["normalize"][1]
    documents, _ = account_extraction(inventory, extraction)
    normalized = account_normalization(documents, normalization)
    check_spans(documents, extraction, inventory)
    check_views(normalized, extraction, normalization)
    mappings, accounting = check_mapping(summary, inventory, extraction, normalized)
    evidence = check_evidence(
        mappings, normalized, documents, normalization, inventory_path, context.silos
    )
    policy = load_classifier_policy(context.project_root)
    runtime = summary["runtime"]
    resources = {
        "throughput": runtime["throughput_files_per_second"]
        >= policy.gates.minimum_throughput_files_per_second,
        "peakMemory": runtime["peak_memory_mib"] <= policy.gates.maximum_peak_memory_mib,
    }
    require(
        summary["reproducibility"]
        == {"status": "pass", "checked_rows": accounting["physicalFiles"]},
        "classifier reproducibility check is incomplete",
    )
    return {
        "accounting": accounting,
        "evidence": evidence,
        "manifest": summary["checked_manifest"],
        "runtime": runtime,
        "resourceGates": resources,
        "upstream": summary["upstream"],
        "classifier": summary["classifier"],
        "scheme": summary["scheme"],
        "producers": summary["checked_producers"],
    }


@pytest.fixture(scope="module")
def classification_context() -> RunContext:
    """Use an explicitly selected run or execute a fresh forecasted classify closure."""
    project_root = find_project_root()
    config = load_runtime_config(project_root=project_root)
    run_id = os.environ.get("ARCHIVE_CLASSIFICATION_RUN_ID")
    context = (
        require_frozen_context(config.runs_dir, run_id, project_root=project_root)
        if run_id
        else create_run_context(project_root=project_root, to_stage="classify")
    )
    require(context.to_stage == "classify", "selected run must end at classify")
    _LOG.warning("archive classification integration run_id=%s", context.run_id)
    registry = production_registry()
    forecast_or_refuse(context, config, registry)
    require(run_dag(context, registry) == 0, "classification closure failed")
    return context


def test_provided_archive_classification_integrity_and_noop_replay(
    classification_context: RunContext,
) -> None:
    """Validate mapping integrity independently of pending human classification judgments."""
    context = classification_context
    project_root = context.project_root
    config = load_runtime_config(project_root=project_root)
    registry = production_registry()
    first = _cross_check(context)
    require(first["accounting"]["physicalFiles"] > 0, "provided archive is empty")
    forecast_or_refuse(context, config, registry)
    require(run_dag(context, registry) == 0, "unchanged classification replay failed")
    replay = load_status(context.runs_dir, context.run_id)
    require(
        all(item.cache_hit and not item.worker_invoked for item in replay.executions),
        "unchanged replay invoked a heavy worker",
    )
    require_frozen_context(config.runs_dir, context.run_id, project_root=project_root)
    require(_cross_check(context) == first, "classification artifacts changed on cache replay")
    log = (
        project_root
        / dict(config.values)["DATA_DIR"]
        / "integration/archive-classification"
        / context.run_id
    )
    write_json(
        log / "integrity.json",
        {
            **first,
            "runId": context.run_id,
            "sourceUnchanged": True,
            "cacheHits": len(replay.executions),
            "replayWorkerInvocations": 0,
            "reviewPacket": str(
                ClassificationLayout.for_run(context.runs_dir, context.run_id).review
            ),
        },
    )
    packet = load_json(
        ClassificationLayout.for_run(context.runs_dir, context.run_id).review
        / "operating-point.json"
    )
    calibration = (
        check_calibration(context)
        if packet.get("evaluation") is not None
        else {"status": "pending-reviewed-labels", "qualityAccepted": False}
    )
    update_review(context, log / "integrity.json", calibration)
    require(all(first["resourceGates"].values()), "classification resource gate failed; see log")


def test_provided_archive_classification_calibration(classification_context: RunContext) -> None:
    """Missing labels fail this acceptance gate; integrity alone cannot stand in for calibration."""
    context = classification_context
    calibration = check_calibration(context)
    config = load_runtime_config(project_root=context.project_root)
    integrity = (
        context.project_root
        / dict(config.values)["DATA_DIR"]
        / "integration/archive-classification"
        / context.run_id
        / "integrity.json"
    )
    require(integrity.is_file(), "run the classification integrity check before packet readiness")
    update_review(context, integrity, calibration)

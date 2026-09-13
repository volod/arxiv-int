"""Synthetic acceptance tests for frozen archive calibration and review readiness."""

import argparse
from pathlib import Path

import pytest

from arxiv_int.classification.evaluation_command import run_evaluate
from arxiv_int.classification.label_command import run_freeze_labels
from arxiv_int.classification.layout import ClassificationLayout, write_jsonl
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import load_json, write_json
from tests.classification.stage_helpers import classify, rows
from tests.integration.classification.review import (
    _inspection_cases,
    check_calibration,
    update_review,
)
from tests.pipeline.chain import run_chain


@pytest.fixture
def calibrated_context(tmp_path: Path) -> RunContext:
    chain = run_chain(
        tmp_path,
        fixtures={
            "ml.txt": "Machine learning artificial intelligence data science",
            "structural.txt": "Structural engineering structural analysis and design",
            "random.txt": "qzxw unrelated random gibberish",
            "blank.txt": "\u200b\n",
        },
    )
    result = classify(chain)
    manifest = chain.manifest(result)
    context = RunContext(
        "run-chain",
        "run-chain",
        "fixture",
        "fixture",
        "fixture",
        chain.context.silos,
        chain.context.results_dir,
        chain.context.results_dir / "runs",
        Path.cwd(),
        {},
        {},
    )
    truth = {
        "ml.txt": "tax:02.03.01",
        "structural.txt": "tax:04.02.01",
        "random.txt": "unclassified",
        "blank.txt": "unreadable",
    }
    gold = tmp_path / "gold.jsonl"
    write_jsonl(
        gold,
        (
            {
                "item_id": row["occurrence_id"],
                "gold_ref": row["relative_path"],
                "primary": truth[str(row["relative_path"])],
                "split": "test",
            }
            for row in rows(manifest)
        ),
    )
    arguments = {
        "project_root": Path.cwd(),
        "runs_dir": context.runs_dir,
        "run_id": context.run_id,
        "label_set": "synthetic-final",
    }
    assert run_freeze_labels(argparse.Namespace(**arguments, scheme=None, labels=gold)) == 0
    labels = (
        ClassificationLayout.for_run(context.runs_dir, context.run_id).evaluation("synthetic-final")
        / "labels.jsonl"
    )
    assert run_evaluate(
        argparse.Namespace(**arguments, labels=labels, classification=manifest, split="test")
    ) in {0, 1}
    return context


def test_frozen_calibration_reproduces_without_self_approval(
    calibrated_context: RunContext,
) -> None:
    result = check_calibration(calibrated_context)
    assert result["status"] in {"measured", "measured-negative"}
    assert result["metrics"]["items"] == 4
    assert result["metrics"]["exact_accuracy"] == 1.0
    assert result["qualityAccepted"] is False


def test_review_cases_keep_outcomes_separate_and_unreviewed(
    calibrated_context: RunContext,
) -> None:
    packet = load_json(
        ClassificationLayout.for_run(calibrated_context.runs_dir, calibrated_context.run_id).review
        / "operating-point.json"
    )
    cases = _inspection_cases(Path(packet["mappingManifest"]["path"]))
    assert {case["primaryProposal"] for case in cases["assigned"]} == {
        "tax:02.03.01",
        "tax:04.02.01",
    }
    assert cases["nearThreshold"][0]["primaryProposal"] == "unclassified"
    assert cases["unreadable"][0]["primaryProposal"] == "unreadable"
    assert all(
        case["goldPrimary"] is None and case["reviewState"] == "unreviewed"
        for cohort in cases.values()
        for case in cohort
    )


def test_missing_calibration_cannot_pass_as_integrity(calibrated_context: RunContext) -> None:
    layout = ClassificationLayout.for_run(calibrated_context.runs_dir, calibrated_context.run_id)
    path = layout.review / "operating-point.json"
    packet = load_json(path)
    packet["evaluation"] = None
    write_json(path, packet)
    with pytest.raises(AssertionError, match="labels/calibration are missing"):
        check_calibration(calibrated_context)


def test_negative_measured_quality_keeps_packet_pending(calibrated_context: RunContext) -> None:
    layout = ClassificationLayout.for_run(calibrated_context.runs_dir, calibrated_context.run_id)
    packet = load_json(layout.review / "operating-point.json")
    integrity = layout.review / "synthetic-integrity.json"
    write_json(
        integrity,
        {
            "manifest": {
                "manifest": packet["mappingManifest"]["path"],
                "sha256": packet["mappingManifest"]["sha256"],
            },
            "resourceGates": {"throughput": True, "peakMemory": True},
            "producers": {},
        },
    )
    update_review(
        calibrated_context,
        integrity,
        {"status": "measured-negative", "qualityGatesPassed": False, "qualityAccepted": False},
    )
    result = load_json(layout.review / "operating-point.json")
    assert result["readiness"] == "pending"
    assert "held-out classification quality gates" in result["pending"]


def test_resealed_incorrect_metrics_are_refused(calibrated_context: RunContext) -> None:
    layout = ClassificationLayout.for_run(calibrated_context.runs_dir, calibrated_context.run_id)
    path = layout.review / "operating-point.json"
    packet = load_json(path)
    report_path = Path(packet["evaluation"]["metrics"])
    report = load_json(report_path)
    report["metrics"]["calibration_error"] = 0.123456789
    write_json(report_path, report)
    packet["evaluation"]["sha256"] = hash_file(report_path)[0]
    write_json(path, packet)
    with pytest.raises(AssertionError, match="metrics do not reproduce"):
        check_calibration(calibrated_context)

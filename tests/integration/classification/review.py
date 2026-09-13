"""Check existing evaluation artifacts and assemble the ordinary human-review packet."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from arxiv_int.classification.artifacts import validate_manifest
from arxiv_int.classification.evaluation import evaluate
from arxiv_int.classification.labels import read_labels
from arxiv_int.classification.layout import ClassificationLayout
from arxiv_int.classification.policy import load_classifier_policy
from arxiv_int.classification.vocabulary.snapshot import load_snapshot
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import load_json, write_json
from tests.integration.corpus.artifacts import require, rows


def check_calibration(context: RunContext) -> dict[str, Any]:
    """Recompute a held-out report from sealed archive labels, refusing missing evidence."""
    layout = ClassificationLayout.for_run(context.runs_dir, context.run_id)
    packet = load_json(layout.review / "operating-point.json")
    reference = packet.get("evaluation")
    require(
        isinstance(reference, dict),
        "reviewed archive labels/calibration are missing; freeze reviewed labels with "
        "make classification-labels, then run make classification-evaluate for this mapping",
    )
    assert isinstance(reference, dict)
    report_path = Path(reference["metrics"])
    require(hash_file(report_path)[0] == reference["sha256"], "evaluation report checksum changed")
    report = load_json(report_path)
    mapping = packet["mappingManifest"]
    require(
        report["classification"] == {"manifest": mapping["path"], "sha256": mapping["sha256"]},
        "evaluation scores a different mapping",
    )
    summary = validate_manifest(Path(mapping["path"]), mapping["sha256"])
    predictions = [
        row for row, _ in rows(Path(summary["roots"]["file-classifications"]), "classification_id")
    ]
    labels = _checked_labels(context, report, summary)
    require(
        report["metrics"]["split"] == "test", "archive quality requires the held-out test split"
    )
    policy = load_classifier_policy(context.project_root)
    require(
        report["classifier"]
        == {
            "classifier_id": policy.classifier_id,
            "configuration_sha256": policy.sha256,
        },
        "evaluation classifier identity is stale",
    )
    recomputed = evaluate(labels, predictions, summary, policy, split="test").as_dict()
    require(
        all(report[key] == value for key, value in recomputed.items()),
        "retained calibration metrics do not reproduce",
    )
    require(reference["passed"] == report["passed"], "review packet evaluation verdict drift")
    return {
        "status": "measured" if report["passed"] else "measured-negative",
        "qualityAccepted": False,
        "qualityGatesPassed": report["passed"],
        "metrics": report["metrics"],
        "reportSha256": reference["sha256"],
    }


def _checked_labels(
    context: RunContext, report: dict[str, Any], summary: dict[str, Any]
) -> list[dict[str, Any]]:
    labels_path = Path(report["labels"]["path"])
    require(hash_file(labels_path)[0] == report["labels"]["sha256"], "evaluation labels changed")
    ledger = load_json(labels_path.parent / "splits.json")
    require(ledger["schemeId"] == summary["scheme"]["scheme_id"], "label scheme is different")
    for name in ("labels.jsonl", "evaluation-items.jsonl"):
        require(
            hash_file(labels_path.parent / name)[0] == ledger["files"][name],
            "frozen label seal is invalid",
        )
    require(labels_path.name == "labels.jsonl", "evaluation did not consume sealed labels")
    labels = read_labels(labels_path)
    require(len(labels) == ledger["items"], "frozen label count mismatch")
    scheme = load_snapshot(ClassificationLayout.for_run(context.runs_dir, context.run_id).scheme)
    content_by_occurrence = {
        row["occurrence_id"]: extra["content_hash"]
        for row, extra in rows(Path(summary["roots"]["file-classifications"]), "classification_id")
    }
    grouped: dict[str, set[str]] = defaultdict(set)
    for label in labels:
        require(label["scheme_id"] == ledger["schemeId"], "label row scheme mismatch")
        require(
            tuple(label["path"]) == scheme.scheme.path(label["primary"]),
            "gold ancestor path does not match its primary",
        )
        require(label["item_id"] in content_by_occurrence, "label is outside supplied archive")
        content = content_by_occurrence[label["item_id"]]
        grouped[str(content or label["group_key"])].add(label["split"])
    require(
        all(len(splits) == 1 for splits in grouped.values()),
        "duplicate content leaks between tuning and held-out labels",
    )
    return labels


def update_review(context: RunContext, integrity_path: Path, calibration: dict[str, Any]) -> None:
    """Attach checked evidence to the existing packet without recording a human decision."""
    layout = ClassificationLayout.for_run(context.runs_dir, context.run_id)
    packet_path = layout.review / "operating-point.json"
    packet = load_json(packet_path)
    integrity = load_json(integrity_path)
    require(
        integrity["manifest"]
        == {
            "manifest": packet["mappingManifest"]["path"],
            "sha256": packet["mappingManifest"]["sha256"],
        },
        "integrity evidence names another mapping",
    )
    pending = []
    if not all(integrity["resourceGates"].values()):
        pending.append("classification resource gates")
    if calibration["status"] == "pending-reviewed-labels":
        pending.append("reviewed archive labels and held-out calibration")
    elif not calibration["qualityGatesPassed"]:
        pending.append("held-out classification quality gates")
    packet.update(
        integrity={"log": str(integrity_path), "sha256": hash_file(integrity_path)[0]},
        calibration=calibration,
        producers=integrity["producers"],
        inspectionCases=_inspection_cases(Path(packet["mappingManifest"]["path"])),
        pending=pending,
        readiness="pending" if pending else "ready",
        decisionRecord=str(layout.review / "decision.json"),
        blockedConsumers=[
            "publish-provided-archive-end-to-end-proof",
            "approve-archive-organization-plan",
        ],
    )
    write_json(packet_path, packet)


def _inspection_cases(manifest: Path) -> dict[str, list[dict[str, Any]]]:
    """Give review a bounded, diverse candidate set without inventing gold labels."""
    summary = load_json(manifest)
    found = [
        row for row, _ in rows(Path(summary["roots"]["file-classifications"]), "classification_id")
    ]
    assigned = sorted(
        (row for row in found if row["primary_class_id"].startswith(("tax:", "ext:"))),
        key=lambda row: (row["primary_class_id"], row["occurrence_id"]),
    )
    unclassified = sorted(
        (row for row in found if row["primary_class_id"] == "unclassified"),
        key=lambda row: (-_best_score(row), row["occurrence_id"]),
    )
    unreadable = sorted(
        (row for row in found if row["primary_class_id"] == "unreadable"),
        key=lambda row: (row["failure_reason"], row["occurrence_id"]),
    )
    ambiguous = sorted(
        (row for row in found if _candidate_gap(row) is not None),
        key=lambda row: (_candidate_gap(row), row["occurrence_id"]),
    )
    return {
        name: [_case(row) for row in cohort[:5]]
        for name, cohort in (
            ("assigned", assigned),
            ("nearThreshold", unclassified),
            ("unreadable", unreadable),
            ("ambiguous", ambiguous),
        )
    }


def _best_score(row: dict[str, Any]) -> float:
    candidates = json.loads(row["scores_json"])
    return float(candidates[0]["score"]) if candidates else 0.0


def _candidate_gap(row: dict[str, Any]) -> float | None:
    candidates = json.loads(row["scores_json"])
    if len(candidates) < 2 or candidates[0]["score"] <= 0.0:
        return None
    return float(candidates[0]["score"]) - float(candidates[1]["score"])


def _case(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "occurrenceId": row["occurrence_id"],
        "relativePath": row["relative_path"],
        "primaryProposal": row["primary_class_id"],
        "confidence": row["confidence"],
        "failureReason": row["failure_reason"],
        "topCandidates": json.loads(row["scores_json"])[:3],
        "evidence": json.loads(row["evidence_json"])[:3],
        "reviewState": "unreviewed",
        "goldPrimary": None,
    }

"""CLI handler for frozen held-out file-classification evaluation."""

import argparse
import logging
from pathlib import Path
from typing import Any, cast

from arxiv_int.classification.artifacts import validate_manifest
from arxiv_int.classification.evaluation import evaluate
from arxiv_int.classification.labels import read_labels
from arxiv_int.classification.layout import ClassificationLayout, command_roots
from arxiv_int.classification.policy import load_classifier_policy
from arxiv_int.features import require_module
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.run.persist import load_json, write_json

_LOG = logging.getLogger(__name__)


def run_evaluate(args: argparse.Namespace) -> int:
    """Validate inputs, compute all predeclared metrics, and publish one report."""
    project_root, runs_dir = command_roots(args)
    manifest_path = Path(args.classification)
    manifest_digest = hash_file(manifest_path)[0]
    manifest = validate_manifest(manifest_path, manifest_digest)
    labels = read_labels(Path(args.labels))
    predictions = _predictions(manifest)
    policy = load_classifier_policy(project_root)
    split = None if args.split == "all" else str(args.split)
    report = evaluate(labels, predictions, manifest, policy, split=split)
    layout = ClassificationLayout.for_run(runs_dir, args.run_id)
    destination = layout.quality_evaluation(args.label_set) / "metrics.json"
    payload: dict[str, Any] = {
        **report.as_dict(),
        "classification": {"manifest": str(manifest_path), "sha256": manifest_digest},
        "classifier": {
            "classifier_id": policy.classifier_id,
            "configuration_sha256": policy.sha256,
        },
        "labels": {"path": str(args.labels), "sha256": hash_file(Path(args.labels))[0]},
        "schema": "arxiv-int.classification-evaluation.v1",
    }
    write_json(destination, payload)
    _update_review(layout, destination, payload)
    _LOG.info(
        "classification evaluation %s: items=%d exact=%.3f hierarchical_f1=%.3f",
        "passed" if report.passed else "failed",
        report.metrics["items"],
        report.metrics["exact_accuracy"],
        report.metrics["hierarchical_f1"],
    )
    return 0 if report.passed else 1


def _predictions(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    root = Path(str(manifest["roots"]["file-classifications"]))
    files = sorted(root.glob("part-*.parquet"))
    if not files:
        return []
    polars = require_module("polars")
    return cast(list[dict[str, Any]], polars.read_parquet(files).to_dicts())


def _update_review(
    layout: ClassificationLayout, destination: Path, evaluation: dict[str, Any]
) -> None:
    packet_path = layout.review / "operating-point.json"
    if not packet_path.is_file():
        return
    packet = load_json(packet_path)
    packet["evaluation"] = {
        "metrics": str(destination),
        "passed": bool(evaluation["passed"]),
        "sha256": hash_file(destination)[0],
    }
    write_json(packet_path, packet)

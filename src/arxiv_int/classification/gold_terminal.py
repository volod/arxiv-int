"""Human-only, resumable gold labeling of a sealed archive classification map."""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, TextIO

from arxiv_int.classification.evaluation_command import run_evaluate
from arxiv_int.classification.gold_interaction import ask, label_one, say
from arxiv_int.classification.label_command import run_freeze_labels
from arxiv_int.classification.labels import read_labels, resolve_label
from arxiv_int.classification.layout import ClassificationLayout, command_roots, safe_id
from arxiv_int.classification.review_material import load_review_material, review_order
from arxiv_int.classification.vocabulary.policy import load_scheme_policy
from arxiv_int.classification.vocabulary.snapshot import check_snapshot, load_snapshot
from arxiv_int.classification.vocabulary.validate import errors
from arxiv_int.pipeline.run.persist import load_json, write_json

DEFAULT_REVIEW_LIMIT = 40


def _paths(layout: ClassificationLayout, label_set: str) -> tuple[Path, Path]:
    stem = f"gold-{safe_id(label_set, 'label set')}"
    return layout.review / f"{stem}.jsonl", layout.review / f"{stem}.meta.json"


def _draft(
    layout: ClassificationLayout, label_set: str, mapping: dict[str, str], scheme_id: str
) -> tuple[Path, list[dict[str, Any]]]:
    labels, metadata = _paths(layout, label_set)
    expected = {
        "schema": "arxiv-int.classification-gold-review.v1",
        "mappingManifest": mapping,
        "schemeId": scheme_id,
        "labelSet": label_set,
    }
    if metadata.exists():
        if load_json(metadata) != expected or not labels.is_file():
            raise ValueError("gold draft identity differs from this sealed mapping; use a new set")
    else:
        if labels.exists():
            raise ValueError("gold JSONL lacks an identity sidecar; refusing to overwrite it")
        layout.review.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(labels, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.close(descriptor)
        write_json(metadata, expected)
    return labels, read_labels(labels)


def _append(path: Path, record: dict[str, Any]) -> None:
    with path.open("a", encoding="ascii") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _finalize(
    project_root: Path,
    runs_dir: Path,
    run_id: str,
    label_set: str,
    gold_path: Path,
    manifest: Path,
    output: TextIO,
) -> int:
    if not read_labels(gold_path):
        raise ValueError("no human-confirmed labels; calibration cannot be frozen")
    args = argparse.Namespace(
        project_root=project_root,
        runs_dir=runs_dir,
        run_id=run_id,
        scheme=None,
        label_set=label_set,
        labels=gold_path,
    )
    if run_freeze_labels(args) != 0:
        return 1
    frozen = ClassificationLayout.for_run(runs_dir, run_id).evaluation(label_set) / "labels.jsonl"
    args.classification = manifest
    args.labels = frozen
    args.split = "test"
    result = run_evaluate(args)
    say(output, f"Human gold JSONL: {gold_path}")
    say(output, f"Frozen labels: {frozen}")
    say(
        output,
        f"Held-out report: {ClassificationLayout.for_run(runs_dir, run_id).quality_evaluation(label_set) / 'metrics.json'}",
    )
    if result != 0:
        say(output, "Calibration gates failed. Review errors; do not accept the operating point.")
    return result


def _review_rows(
    mapping: list[tuple[dict[str, Any], dict[str, Any]]],
    limit: int,
    labels: Path,
    reviewed: set[str],
    scheme: Any,
    scheme_policy: Any,
    views: dict[str, str],
    input_stream: TextIO,
    output: TextIO,
) -> bool:
    """Return false when the operator pauses instead of finishing the batch."""
    for row, extra in review_order(mapping, limit):
        if row["occurrence_id"] in reviewed:
            continue
        choice = label_one(row, extra, scheme, scheme_policy, views, input_stream, output)
        if choice == "q":
            say(output, "Review paused; rerun the same command to resume.")
            return False
        if choice == "f":
            break
        if choice == "s":
            continue
        if not isinstance(choice, dict):
            raise ValueError("unexpected review choice")
        _append(labels, choice)
        reviewed.add(row["occurrence_id"])
    return True


def review_gold(
    project_root: Path,
    runs_dir: Path,
    run_id: str,
    label_set: str,
    limit: int,
    input_stream: TextIO,
    output: TextIO,
) -> int:
    """Gather explicit human labels, then freeze and score only on request."""
    layout = ClassificationLayout.for_run(runs_dir, run_id)
    packet = load_json(layout.review / "operating-point.json")
    reference = packet.get("mappingManifest")
    if not isinstance(reference, dict):
        raise ValueError("this run has no sealed classification mapping")
    manifest = Path(str(reference["path"]))
    summary, mapping, views = load_review_material(manifest, str(reference["sha256"]))
    scheme_policy = load_scheme_policy(project_root)
    if errors(check_snapshot(layout.scheme, scheme_policy)):
        raise ValueError("scheme is stale or damaged; create a fresh run")
    scheme = load_snapshot(layout.scheme).scheme
    labels, existing = _draft(layout, label_set, reference, summary["scheme"]["scheme_id"])
    ids = {row["occurrence_id"] for row, _ in mapping}
    reviewed = {record["item_id"] for record in existing}
    if len(reviewed) != len(existing) or not reviewed <= ids:
        raise ValueError("gold draft has duplicate or foreign item ids")
    for record in existing:
        resolve_label(record, scheme, scheme_policy)
    say(
        output,
        f"Gold review: {len(reviewed)} confirmed, {len(mapping)} physical files; draft {labels}",
    )
    say(output, "Only an explicit 'yes' writes a gold label. Quit preserves progress.")
    if not _review_rows(
        mapping, limit, labels, reviewed, scheme, scheme_policy, views, input_stream, output
    ):
        return 2
    if (
        ask(input_stream, output, "Type freeze to seal labels and score held-out test: ")
        != "freeze"
    ):
        say(output, "Review paused; no label set frozen.")
        return 2
    return _finalize(project_root, runs_dir, run_id, label_set, labels, manifest, output)


def run_gold_review(args: argparse.Namespace) -> int:
    """CLI adapter requiring a terminal for independently reviewed labels."""
    if not sys.stdin.isatty():
        raise ValueError("gold review needs a terminal")
    root, runs_dir = command_roots(args)
    return review_gold(
        root,
        runs_dir,
        str(args.run_id),
        str(args.label_set),
        int(args.limit),
        sys.stdin,
        sys.stdout,
    )

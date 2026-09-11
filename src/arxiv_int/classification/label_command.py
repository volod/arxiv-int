"""CLI handler for ``arxiv-int classification freeze-labels``."""

import argparse
import logging
from pathlib import Path

from arxiv_int.classification.labels import (
    GoldLabel,
    LabelError,
    assign_splits,
    evaluation_item_row,
    label_row,
    read_labels,
    resolve_label,
    split_ledger,
)
from arxiv_int.classification.layout import (
    ClassificationLayout,
    command_roots,
    safe_id,
    scheme_directory,
    validate_contract_rows,
    write_jsonl,
)
from arxiv_int.classification.vocabulary.model import Scheme
from arxiv_int.classification.vocabulary.policy import SchemePolicy, load_scheme_policy
from arxiv_int.classification.vocabulary.snapshot import check_snapshot, load_snapshot
from arxiv_int.classification.vocabulary.validate import errors
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.run.persist import write_json

EVALUATION_CONTRACT = "evaluation-items"
LABELS_FILE = "labels.jsonl"
ITEMS_FILE = "evaluation-items.jsonl"
LEDGER_FILE = "splits.json"
_LOG = logging.getLogger(__name__)


def _resolve_all(
    records: list[dict[str, object]], scheme: Scheme, policy: SchemePolicy
) -> tuple[list[GoldLabel], list[str]]:
    labels: list[GoldLabel] = []
    problems: list[str] = []
    for index, record in enumerate(records, start=1):
        try:
            labels.append(resolve_label(record, scheme, policy))
        except LabelError as error:
            problems.append(f"label {index} ({record.get('item_id')}): {error}")
    return labels, problems


def run_freeze_labels(args: argparse.Namespace) -> int:
    """Validate a gold label file against a current scheme and freeze its splits."""
    project_root, runs_dir = command_roots(args)
    policy = load_scheme_policy(project_root)
    label_set = safe_id(args.label_set, "label set")
    directory = scheme_directory(args, runs_dir)
    if errors(check_snapshot(directory, policy)):
        _LOG.error("refusing labels against a stale or damaged scheme; run check-scheme")
        return 1
    snapshot = load_snapshot(directory)
    labels_path = Path(args.labels)
    labels, problems = _resolve_all(read_labels(labels_path), snapshot.scheme, policy)
    for problem in problems:
        _LOG.error("%s", problem)
    if problems or not labels:
        _LOG.error("no labels frozen: %d problem(s), %d valid label(s)", len(problems), len(labels))
        return 1
    labels = assign_splits(labels, policy)
    scheme_id = str(snapshot.manifest["schemeId"])
    items = [evaluation_item_row(label, label_set, args.run_id) for label in labels]
    validate_contract_rows(project_root, EVALUATION_CONTRACT, items)
    output = ClassificationLayout.for_run(runs_dir, args.run_id).evaluation(label_set)
    if output.exists() and any(output.iterdir()):
        raise LabelError(f"label set {label_set} is already frozen in this run")
    output.mkdir(parents=True, exist_ok=True)
    write_jsonl(output / LABELS_FILE, (label_row(label, scheme_id) for label in labels))
    write_jsonl(output / ITEMS_FILE, items)
    ledger = split_ledger(labels, policy)
    ledger.update(
        files={name: hash_file(output / name)[0] for name in (LABELS_FILE, ITEMS_FILE)},
        labelSetId=label_set,
        labelsFile={"name": labels_path.name, "sha256": hash_file(labels_path)[0]},
        schemeId=scheme_id,
        schemeVersion=snapshot.manifest.get("schemeVersion"),
    )
    write_json(output / LEDGER_FILE, ledger)
    _LOG.info(
        "froze %d label(s) in %d group(s) for %s: %s",
        ledger["items"],
        ledger["groups"],
        scheme_id,
        ", ".join(f"{split}={sum(c.values())}" for split, c in ledger["counts"].items()),
    )
    return 0

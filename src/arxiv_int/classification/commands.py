"""CLI handlers for ``arxiv-int classification``."""

import argparse
import logging
import sys
from collections import Counter
from collections.abc import Sequence

from arxiv_int.classification.label_command import run_freeze_labels
from arxiv_int.classification.layout import (
    ClassificationLayout,
    command_roots,
    scheme_directory,
    validate_contract_rows,
)
from arxiv_int.classification.vocabulary.build import build_scheme, taxonomy_classes
from arxiv_int.classification.vocabulary.describe import describe_class, tree_lines
from arxiv_int.classification.vocabulary.model import Scheme
from arxiv_int.classification.vocabulary.policy import load_scheme_policy
from arxiv_int.classification.vocabulary.review import vocabulary_packet
from arxiv_int.classification.vocabulary.snapshot import (
    check_snapshot,
    load_snapshot,
    write_snapshot,
)
from arxiv_int.classification.vocabulary.validate import SEVERITY_WARNING, Finding, errors
from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.pipeline.run.persist import write_json

EXIT_OK = 0
EXIT_FAILED = 1
CLASSES_CONTRACT = "classification-classes"
REVIEW_FILE = "vocabulary.json"
_LOG = logging.getLogger(__name__)


def log_findings(findings: Sequence[Finding]) -> None:
    """Log every blocking finding and a per-code warning count."""
    for item in errors(findings):
        _LOG.error("%s %s: %s", item.code, item.class_id or "-", item.message)
    warnings = Counter(item.code for item in findings if item.severity == SEVERITY_WARNING)
    for code, count in sorted(warnings.items()):
        _LOG.warning("%s: %d warning(s); see report.json", code, count)


def _build(args: argparse.Namespace) -> int:
    project_root, runs_dir = command_roots(args)
    policy = load_scheme_policy(project_root)
    layout = ClassificationLayout.for_run(runs_dir, args.run_id)
    built = build_scheme(policy, run_id=args.run_id)
    if built.publishable:
        validate_contract_rows(project_root, CLASSES_CONTRACT, built.rows)
    write_snapshot(layout.scheme, built)
    log_findings(built.findings)
    if not built.publishable:
        _LOG.error("scheme not published; see classification/scheme/report.json")
        return EXIT_FAILED
    packet = vocabulary_packet(
        built.manifest,
        built.rows,
        inspect_command=f"arxiv-int classification tree --run-id {args.run_id}",
    )
    write_json(layout.review / REVIEW_FILE, packet)
    balance = built.manifest["balance"]
    _LOG.info(
        "published scheme %s: %d classes, %d leaves, max domain share %.2f, coverage %s",
        built.scheme_id,
        built.manifest["counts"]["classes"],
        balance["leaves"],
        balance["maxDomainLeafShare"],
        ", ".join(
            f"{item['sourceId']} {item['mapped']}/{item['items']}"
            for item in built.manifest["coverage"]
        ),
    )
    return EXIT_OK


def _check(args: argparse.Namespace) -> int:
    project_root, runs_dir = command_roots(args)
    findings = check_snapshot(
        scheme_directory(args, runs_dir),
        load_scheme_policy(project_root),
        expect_scheme_id=args.expect_scheme_id,
    )
    log_findings(findings)
    if errors(findings):
        return EXIT_FAILED
    _LOG.info("scheme snapshot is intact and current")
    return EXIT_OK


def _show(args: argparse.Namespace) -> int:
    project_root, runs_dir = command_roots(args)
    directory = scheme_directory(args, runs_dir)
    if errors(check_snapshot(directory, load_scheme_policy(project_root))):
        _LOG.warning("scheme snapshot is stale or damaged; run check-scheme before relying on it")
    snapshot = load_snapshot(directory)
    rows = {str(row["class_id"]): row for row in snapshot.rows}
    described = describe_class(snapshot.scheme, rows, snapshot.manifest, args.target)
    sys.stdout.write(normalize_json(described))
    return EXIT_OK


def _tree(args: argparse.Namespace) -> int:
    project_root, runs_dir = command_roots(args)
    if args.scheme is None and args.run_id is None:
        scheme = Scheme.of(taxonomy_classes(load_scheme_policy(project_root)))
    else:
        scheme = load_snapshot(scheme_directory(args, runs_dir)).scheme
    for line in tree_lines(scheme, args.root, args.depth):
        sys.stdout.write(line + "\n")
    return EXIT_OK


_HANDLERS = {
    "build-scheme": _build,
    "check-scheme": _check,
    "freeze-labels": run_freeze_labels,
    "show": _show,
    "tree": _tree,
}


def run_classification_command(args: argparse.Namespace) -> int:
    """Run one classification scheme command."""
    try:
        return _HANDLERS[str(args.classification_command)](args)
    except (OSError, RuntimeError, ValueError) as problem:
        _LOG.error("%s", problem)
        return EXIT_FAILED

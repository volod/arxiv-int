"""CLI handlers for evaluate, fixtures, and proof dispatch."""

import argparse
import logging

from arxiv_int.evaluation.eval_errors import EvaluationError
from arxiv_int.evaluation.eval_paths import fixture_root
from arxiv_int.evaluation.evaluate_run import EvaluateRequest, run_evaluate
from arxiv_int.evaluation.families import (
    all_items,
    fixture_drift,
    load_fixture_catalog,
    write_fixture_catalog,
)
from arxiv_int.evaluation.fixture_guard import item_ledger
from arxiv_int.evaluation.proof_ops import (
    check_capability_proof,
    discover_proof_targets,
    publish_capability_proof,
    write_capability_registry,
    write_threshold_config,
)
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root

_LOG = logging.getLogger(__name__)


def run_evaluate_cli(args: argparse.Namespace) -> int:
    """Dispatch evaluate, fixtures, and proof subcommands."""
    try:
        root = find_project_root(args.project_root)
        command = args.evaluation_command
        if command == "evaluate":
            return _evaluate(args, root)
        if command == "fixtures":
            return _fixtures(args, root)
        return _proof(args, root)
    except (EvaluationError, OSError, ProjectRootError, ValueError) as error:
        _LOG.error("%s", error)
        return 1


def _evaluate(args: argparse.Namespace, root: object) -> int:
    from pathlib import Path

    project_root = Path(str(root))
    gold = args.fixture_root or fixture_root(project_root)
    outcome = run_evaluate(
        EvaluateRequest(
            run_id=args.run_id,
            project_root=project_root,
            fixture_root=gold,
            runs_dir=args.runs_dir,
            seed=args.seed,
        )
    )
    _LOG.info(
        "published evaluation bundle fingerprint=%s verdict=%s",
        outcome.bundle.fingerprint,
        outcome.verdict,
    )
    return 0


def _fixtures(args: argparse.Namespace, root: object) -> int:
    from pathlib import Path

    project_root = Path(str(root))
    if args.fixtures_command == "generate":
        written = write_fixture_catalog(fixture_root(project_root))
        write_capability_registry(project_root)
        write_threshold_config(project_root)
        _LOG.info("wrote %d fixture documents", len(written))
        return 0
    findings = fixture_drift(project_root)
    from arxiv_int.evaluation.bundle_manifest import canonical_json
    from arxiv_int.evaluation.eval_paths import proof_config_path, threshold_config_path
    from arxiv_int.evaluation.proof_model import capability_registry_document
    from arxiv_int.evaluation.proof_ops import threshold_document

    registry_path = proof_config_path(project_root)
    if not registry_path.is_file() or registry_path.read_bytes() != canonical_json(
        capability_registry_document()
    ):
        findings.append("drift in configs/proofs/capabilities.json")
    thresholds = threshold_config_path(project_root)
    if not thresholds.is_file() or thresholds.read_bytes() != canonical_json(threshold_document()):
        findings.append("drift in configs/evaluation/thresholds.json")
    if findings:
        for finding in findings:
            _LOG.error("%s", finding)
        return 1
    _LOG.info("evaluation fixture catalog drift check passed")
    return 0


def _proof(args: argparse.Namespace, root: object) -> int:
    from pathlib import Path

    project_root = Path(str(root))
    if args.proof_command == "discover":
        for target in discover_proof_targets(project_root):
            stages = ",".join(target.usable_stages)
            _LOG.info("%s kind=%s stages=%s", target.capability_id, target.proof_kind, stages)
        return 0
    if args.proof_command == "generate-registry":
        path = write_capability_registry(project_root)
        write_threshold_config(project_root)
        _LOG.info("wrote proof registry %s", path)
        return 0
    if args.proof_command == "publish":
        published = publish_capability_proof(
            project_root=project_root,
            capability=args.capability,
            run_id=args.run_id,
            results_dir=args.results_dir,
            runs_dir=args.runs_dir,
            fixture_dir=args.fixture_root,
        )
        _LOG.info(
            "published proof fingerprint=%s summary=%s", published.fingerprint, published.summary
        )
        return 0
    families = load_fixture_catalog(fixture_root(project_root))
    ledger = item_ledger(all_items(families))
    fingerprint = check_capability_proof(args.proof_dir, project_root, ledger.fingerprint)
    _LOG.info("proof check passed fingerprint=%s", fingerprint)
    return 0

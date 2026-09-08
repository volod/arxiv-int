"""CLI handlers for proof identity export and policy drift checks."""

import argparse
import logging

from arxiv_int.evaluation.cli import parse_export_maps
from arxiv_int.evaluation.export.errors import ExportError
from arxiv_int.evaluation.export.exporter import ExportMapping, ExportRequest, export_proof_bundle
from arxiv_int.evaluation.export.policy import check_policy_drift, generate_policy
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root

_LOG = logging.getLogger(__name__)


def run_evaluation_command(args: argparse.Namespace) -> int:
    """Dispatch `arxiv-int evaluation` subcommands."""
    try:
        if args.evaluation_command == "identity-policy":
            return _run_policy(args)
        if args.evaluation_command == "export-proof":
            return _run_export(args)
        from arxiv_int.evaluation.evaluate.commands import run_evaluate_cli

        return run_evaluate_cli(args)
    except (ExportError, OSError, ProjectRootError, ValueError) as error:
        _LOG.error("%s", error)
        return 1


def _run_policy(args: argparse.Namespace) -> int:
    root = find_project_root(args.project_root)
    if args.identity_policy_command == "generate":
        path = generate_policy(root)
        _LOG.info("wrote proof-identity policy %s", path)
        return 0
    findings = check_policy_drift(root)
    if findings:
        for finding in findings:
            _LOG.error("%s", finding)
        return 1
    _LOG.info("proof-identity policy drift check passed")
    return 0


def _run_export(args: argparse.Namespace) -> int:
    root = find_project_root(args.project_root)
    mappings = tuple(
        ExportMapping(source, destination) for source, destination in parse_export_maps(args.map)
    )
    published = export_proof_bundle(
        ExportRequest(
            source_bundle=args.source_bundle,
            mappings=mappings,
            run_id=args.run_id,
            project_root=root,
            destination_root=args.destination_root,
            receipt=args.receipt,
        )
    )
    _LOG.info(
        "exported %d proof artifact(s); source=%s export=%s",
        len(published.files),
        published.source_fingerprint[:12],
        published.export_fingerprint[:12],
    )
    _LOG.info("diagnostics: %s", published.diagnostics)
    return 0

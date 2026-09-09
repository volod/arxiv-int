"""CLI handlers for ``arxiv-int archive locate`` and ``archive import-ledger``."""

import argparse
import logging
import sys
from pathlib import Path

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.query.evidence.catalog import (
    default_catalog_path,
    default_ledger_path,
    load_catalog,
    load_ledger,
)
from arxiv_int.query.evidence.ledger import import_ledger
from arxiv_int.query.evidence.model import EvidenceError
from arxiv_int.query.evidence.render import console_lines, import_lines, json_document
from arxiv_int.query.evidence.resolve import resolve_citation
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.project_root import ProjectRootError

_LOG = logging.getLogger(__name__)


def run_archive_command(args: argparse.Namespace) -> int:
    """Dispatch read-only locate or explicit path-event import."""
    try:
        command = str(args.archive_command or "")
        if command == "locate":
            return _run_locate(args)
        if command == "import-ledger":
            return _run_import(args)
        raise EvidenceError("archive requires locate or import-ledger")
    except (EvidenceError, OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return int(getattr(error, "exit_code", 1))


def _run_locate(args: argparse.Namespace) -> int:
    catalog_path, ledger_path, silo_roots = _locate_inputs(args)
    catalog = load_catalog(catalog_path)
    _ledger_id, events = load_ledger(ledger_path)
    if events:
        catalog = catalog.with_events(events)
    resolution = resolve_citation(
        catalog,
        str(args.token).strip(),
        kind=str(args.kind or "content"),
        silo_roots=silo_roots,
    )
    if bool(args.json):
        sys.stdout.write(json_document(resolution))
    else:
        for line in console_lines(resolution):
            _LOG.info("%s", line)
    if not resolution.document_id or not resolution.locations:
        return 1
    return 0


def _run_import(args: argparse.Namespace) -> int:
    source = Path(args.source)
    ledger = args.ledger
    if ledger is None:
        destination = default_ledger_path(_load_runtime(args).results_dir)
    else:
        destination = Path(ledger)
    report = import_ledger(source, destination, ledger_id=str(args.ledger_id or ""))
    if bool(args.json):
        sys.stdout.write(
            normalize_json(
                {
                    "findings": list(report.findings),
                    "inserted": report.inserted,
                    "ledger_id": report.ledger_id,
                    "refused": report.refused,
                    "schema": report.schema,
                    "skipped": report.skipped,
                }
            )
        )
    else:
        for line in import_lines(report):
            _LOG.info("%s", line)
    return 1 if report.refused else 0


def _locate_inputs(args: argparse.Namespace) -> tuple[Path, Path, dict[str, Path]]:
    catalog = args.catalog
    ledger = args.ledger
    silo_roots = _parse_silos(args.silo)
    if catalog is not None:
        ledger_path = (
            Path(ledger) if ledger is not None else Path(catalog).with_name("path-events.json")
        )
        return Path(catalog), ledger_path, silo_roots
    results_dir = _load_runtime(args).results_dir
    catalog_path = Path(catalog) if catalog is not None else default_catalog_path(results_dir)
    ledger_path = Path(ledger) if ledger is not None else default_ledger_path(results_dir)
    return catalog_path, ledger_path, silo_roots


def _parse_silos(values: list[str] | None) -> dict[str, Path]:
    roots: dict[str, Path] = {}
    for item in values or []:
        if "=" not in item:
            raise EvidenceError("silo override must be SILO_ID=ROOT")
        silo_id, raw = item.split("=", 1)
        if not silo_id.strip() or not raw.strip():
            raise EvidenceError("silo override must be SILO_ID=ROOT")
        roots[silo_id.strip()] = Path(raw)
    return roots


def _load_runtime(args: argparse.Namespace) -> RuntimeConfig:
    from arxiv_int.runtime import load_runtime_config

    return load_runtime_config(project_root=args.project_root)

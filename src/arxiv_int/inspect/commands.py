"""CLI handler for ``arxiv-int inspect`` and ``arxiv-int run artifacts``."""

import logging
import sys
from pathlib import Path

from arxiv_int.inspect.lookup import InspectError, resolve_target
from arxiv_int.inspect.model import DEFAULT_LIMIT, DEVELOPMENT_ALIASES
from arxiv_int.inspect.render import console_lines, json_document
from arxiv_int.inspect.summarize import inspect_target
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root

_LOG = logging.getLogger(__name__)


def run_inspect_command(args: object) -> int:
    """Dispatch a read-only inspect of a run, dataset, or latest generation."""
    try:
        return _run(args)
    except (InspectError, OSError, ProjectRootError, RuntimeError, ValueError) as error:
        _LOG.error("%s", error)
        return int(getattr(error, "exit_code", 1))


def _run(args: object) -> int:
    token = str(getattr(args, "target", None) or getattr(args, "run_id", "") or "").strip()
    if not token:
        raise InspectError("inspect requires a run id, dataset id, or latest")
    if token.lower() in DEVELOPMENT_ALIASES:
        raise InspectError("refusing developer alias; use the id from arxiv-int run create")
    limit = int(getattr(args, "limit", DEFAULT_LIMIT) or DEFAULT_LIMIT)
    project_root, runs_dir, results_dir = _inspect_roots(args)
    target = resolve_target(token, runs_dir)
    summary = inspect_target(
        target,
        runs_dir=runs_dir,
        results_dir=results_dir,
        project_root=project_root,
        limit=limit,
    )
    if bool(getattr(args, "json", False)):
        sys.stdout.write(json_document(summary))
        return 0
    for line in console_lines(summary):
        _LOG.info("%s", line)
    return 0


def _inspect_roots(args: object) -> tuple[Path, Path, Path]:
    """Resolve inspect roots; explicit run paths skip operator archive/pgdata."""
    project_root_arg = getattr(args, "project_root", None)
    runs_override = getattr(args, "runs_dir", None)
    results_override = getattr(args, "results_dir", None)
    if runs_override is not None:
        results_dir = (
            Path(results_override) if results_override is not None else Path(runs_override)
        )
        return find_project_root(project_root_arg), Path(runs_override), results_dir
    cli: dict[str, str | None] = {}
    if results_override is not None:
        cli["RESULTS_DIR"] = str(results_override)
    config = load_runtime_config(project_root=project_root_arg, cli=cli)
    return config.project_root, config.runs_dir, Path(results_override or config.results_dir)

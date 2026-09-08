"""Seal a generation, write diagnostics, and activate only a complete profile."""

import logging
from dataclasses import replace
from pathlib import Path

from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.locking import pipeline_lock
from arxiv_int.pipeline.persist import RunStatus, load_status, run_dir
from arxiv_int.pipeline.publish.assemble import assemble_knowledge_base
from arxiv_int.pipeline.publish.model import EXIT_BY_STATUS, KnowledgeBase, PipelineProfile
from arxiv_int.pipeline.publish.pointer import (
    ActivationRefusedError,
    Injector,
    activate_generation,
    reconcile_orphans,
    save_knowledge_base,
)
from arxiv_int.pipeline.publish.profiles import load_profile
from arxiv_int.pipeline.publish.report import write_report
from arxiv_int.pipeline.publish.verify import verified_status

_LOG = logging.getLogger(__name__)


def finalize_run(
    context: RunContext,
    *,
    profile: PipelineProfile | None = None,
    fallback_exit: int = 1,
    injector: Injector | None = None,
) -> int:
    """Write the knowledge-base and report; activate only a succeeded generation."""
    with pipeline_lock(context.runs_dir):
        selected = profile or load_profile(context.profile, context.project_root)
        status_path = run_dir(context.runs_dir, context.run_id) / "status.json"
        if not status_path.is_file():
            return fallback_exit
        status = load_status(context.runs_dir, context.run_id)
        document, code = finalize_status(context, status, selected, injector=injector)
        _emit(document)
        return code


def finalize_status(
    context: RunContext,
    status: RunStatus,
    profile: PipelineProfile,
    *,
    injector: Injector | None = None,
) -> tuple[KnowledgeBase, int]:
    """Finalize from an in-memory DAG walk; used by fixture tests."""
    with pipeline_lock(context.runs_dir):
        reconcile_orphans(context.runs_dir)
        status = verified_status(context, status, profile)
        document = assemble_knowledge_base(context, status, profile)
        save_knowledge_base(context.runs_dir, document)
        write_report(context.runs_dir, document)
        if document.status == "succeeded":
            document = _activate(context.runs_dir, document, injector)
        return document, EXIT_BY_STATUS[document.status]


def _activate(
    runs_dir: Path,
    document: KnowledgeBase,
    injector: Injector | None,
) -> KnowledgeBase:
    try:
        return activate_generation(runs_dir, document, injector=injector)
    except ActivationRefusedError:
        return replace(document, status="failed", active=False)


def _emit(document: KnowledgeBase) -> None:
    _LOG.info("run_id=%s", document.run_id)
    _LOG.info("status=%s", document.status)
    _LOG.info("knowledge_base=%s", document.run_id + "/knowledge-base.json")
    _LOG.info("report=%s", document.report_path)
    _LOG.info("status_command=%s", document.status_command)
    _LOG.info("resume_command=%s", document.resume_command)
    if document.active:
        _LOG.info("active_generation=%s", document.generation_id)

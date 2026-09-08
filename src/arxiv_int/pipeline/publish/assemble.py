"""Build a knowledge-base document from a DAG walk and a declared profile."""

from dataclasses import replace
from pathlib import Path

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.control.artifacts import sha256_text_bytes
from arxiv_int.pipeline.publish.codec import document_payload
from arxiv_int.pipeline.publish.model import (
    REPORT_HTML,
    SCHEMA_ID,
    Coverage,
    KnowledgeBase,
    OutputEntry,
    OutputFamily,
    PipelineProfile,
)
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import RunStatus, StageExecution


def assemble_knowledge_base(
    context: RunContext,
    status: RunStatus,
    profile: PipelineProfile,
) -> KnowledgeBase:
    """Seal ids, checksums, coverage, and honest status for one generation."""
    by_stage = {item.stage: item for item in status.executions}
    outputs = tuple(_entry(family, by_stage, status.not_selected) for family in profile.families)
    logical = _logical_status(status, outputs, profile)
    document = KnowledgeBase(
        schema=SCHEMA_ID,
        run_id=context.run_id,
        generation_id=context.generation_id,
        profile=profile.name,
        status=logical,
        active=False,
        source_snapshot=context.source_snapshot,
        config_fingerprint=context.config_fingerprint,
        fingerprint="",
        outputs=outputs,
        coverage=_coverage(outputs, status.not_selected),
        limitations=_limitations(logical, outputs, status),
        not_selected=status.not_selected,
        report_path=_report_path(profile, outputs),
        status_command=f"arxiv-int run status {context.run_id}",
        resume_command=f"arxiv-int run resume {context.run_id}",
        catalog_path="",
    )
    return replace(document, fingerprint=fingerprint_document(document))


def fingerprint_document(document: KnowledgeBase) -> str:
    """Hash a serialized document after clearing the fingerprint field."""
    payload = document_payload(document)
    payload["fingerprint"] = ""
    payload["active"] = False
    payload["catalog_path"] = ""
    return sha256_text(normalize_json(payload))


def _entry(
    family: OutputFamily,
    by_stage: dict[str, StageExecution],
    not_selected: tuple[str, ...],
) -> OutputEntry:
    if family.stage in not_selected:
        return OutputEntry(family.family_id, family.stage, "", "", 0, None, "not-selected", False)
    execution = by_stage.get(family.stage)
    if execution is None:
        return OutputEntry(
            family.family_id, family.stage, "", "", 0, None, "missing", family.required
        )
    path, checksum, size = _payload_identity(execution)
    usable = execution.outcome in {"produced", "empty", "partial"}
    return OutputEntry(
        family.family_id,
        family.stage,
        (family.path or path) if usable else path,
        checksum,
        size,
        1 if execution.outcome == "produced" else 0,
        execution.outcome,
        family.required,
    )


def _payload_identity(execution: StageExecution) -> tuple[str, str, int]:
    path = execution.directory or ""
    checksum = ""
    size = execution.bytes
    if not path:
        return path, checksum, size
    payload = Path(path) / "stage.json"
    if payload.is_file():
        checksum = sha256_text_bytes(payload.read_bytes())
        size = payload.stat().st_size
        path = str(payload)
    return path, checksum, size


def _logical_status(
    status: RunStatus,
    outputs: tuple[OutputEntry, ...],
    profile: PipelineProfile,
) -> str:
    if status.halt_reason == "interrupted":
        return "interrupted"
    required = tuple(item for item in outputs if item.required)
    if any(item.outcome in {"failed", "not-selected"} for item in required):
        return "failed"
    if any(item.outcome == "partial" for item in required):
        return "partial"
    if any(item.outcome == "missing" for item in required):
        return "failed" if status.halted else "partial"
    if status.halted:
        return "failed"
    expected = set(profile.required_stages)
    executed = {item.stage for item in status.executions}
    if expected - executed:
        return "partial"
    return "succeeded"


def _coverage(outputs: tuple[OutputEntry, ...], not_selected: tuple[str, ...]) -> Coverage:
    required = tuple(item for item in outputs if item.required)
    return Coverage(
        required_families=len(required),
        produced=sum(item.outcome == "produced" for item in required),
        empty=sum(item.outcome == "empty" for item in required),
        partial=sum(item.outcome == "partial" for item in required),
        failed=sum(item.outcome == "failed" for item in required),
        missing=sum(item.outcome == "missing" for item in required),
        not_selected=len(not_selected),
    )


def _limitations(
    logical: str,
    outputs: tuple[OutputEntry, ...],
    status: RunStatus,
) -> tuple[str, ...]:
    notes: list[str] = []
    if logical != "succeeded":
        notes.append(f"generation status is {logical}")
    if status.halt_reason:
        notes.append(status.halt_reason)
    for item in outputs:
        if item.required and item.outcome not in {"produced", "empty"}:
            notes.append(f"{item.family}:{item.outcome}")
    if status.not_selected:
        notes.append("not-selected=" + ",".join(status.not_selected))
    return tuple(dict.fromkeys(notes))


def _report_path(profile: PipelineProfile, outputs: tuple[OutputEntry, ...]) -> str:
    for item in outputs:
        if item.family == profile.report_family and item.outcome in {"produced", "empty"}:
            return item.path or REPORT_HTML
    return REPORT_HTML

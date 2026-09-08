"""Recheck retained evidence at the final publication boundary."""

from dataclasses import replace

from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.execute import try_reuse
from arxiv_int.pipeline.persist import RunStatus
from arxiv_int.pipeline.publish.model import PipelineProfile
from arxiv_int.pipeline.reuse_index import load_reuse_index


def verified_status(context: RunContext, status: RunStatus, profile: PipelineProfile) -> RunStatus:
    """Fail closed when status no longer names a complete validated artifact tree."""
    if status.run_id != context.run_id or status.generation_id != context.generation_id:
        return replace(status, halted=True, halt_reason="run identity mismatch")
    if set(profile.required_stages) & set(status.not_selected):
        return replace(status, halted=True, halt_reason="required stage not selected")
    index = load_reuse_index(context.runs_dir)
    for execution in status.executions:
        if execution.outcome not in {"produced", "empty"}:
            continue
        entry = index.get(execution.reuse_key)
        reused = try_reuse(entry, force=False)
        if (
            reused is None
            or reused.directory != execution.directory
            or reused.attempt != execution.attempt
            or reused.outcome != execution.outcome
            or execution.status not in {"succeeded", "quarantined"}
        ):
            return replace(
                status, halted=True, halt_reason=f"invalid artifact evidence: {execution.stage}"
            )
    return status

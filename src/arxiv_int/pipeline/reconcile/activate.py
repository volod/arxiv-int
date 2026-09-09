"""Quality-gated pointer switch after incremental update or rebuild."""

from collections.abc import Sequence
from pathlib import Path

from arxiv_int.pipeline.control.quality import ActivationDecision, activation_decision
from arxiv_int.pipeline.publish.model import KnowledgeBase
from arxiv_int.pipeline.publish.pointer import ActivationRefusedError, activate_generation
from arxiv_int.pipeline.run.persist import StageExecution


def executions_ready(executions: Sequence[StageExecution]) -> bool:
    """Return whether every walked shard may switch an active pointer."""
    if not executions:
        return False
    return all(
        item.status in {"succeeded", "quarantined"} and item.outcome in {"produced", "empty"}
        for item in executions
    )


def require_quality_switch(decision: ActivationDecision) -> None:
    """Refuse a pointer switch when required checks did not pass."""
    if not decision.allowed:
        raise ActivationRefusedError(
            "refusing pointer switch; quality blocking: " + ", ".join(decision.blocking)
        )


def activate_after_quality(
    runs_dir: Path,
    document: KnowledgeBase,
    executions: Sequence[StageExecution],
    decision: ActivationDecision | None = None,
) -> KnowledgeBase:
    """Activate only after DAG success and required quality checks."""
    if not executions_ready(executions):
        raise ActivationRefusedError("refusing pointer switch; replacements are incomplete")
    chosen = decision or activation_decision((), generation_id=document.generation_id)
    require_quality_switch(chosen)
    return activate_generation(runs_dir, document)

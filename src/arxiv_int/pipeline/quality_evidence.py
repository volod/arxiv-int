"""Revalidate retained producer quality without invoking a heavy worker."""

from pathlib import Path

from arxiv_int.interfaces.stores import TransformationRunRef, ValidationResultRef
from arxiv_int.pipeline.control.quality import QualityCheck, activation_decision
from arxiv_int.pipeline.persist import load_json


def validate_quality_evidence(directory: Path, generation_id: str) -> bool:
    """Require global checks and references for the exact producing generation."""
    try:
        payload = load_json(directory / "quality.json")
        if payload["generation_id"] != generation_id:
            return False
        decision = activation_decision(
            tuple(QualityCheck(**item) for item in payload["checks"]),
            validations=tuple(ValidationResultRef(**item) for item in payload["validations"]),
            transformations=tuple(
                TransformationRunRef(**item) for item in payload["transformations"]
            ),
            generation_id=generation_id,
        )
        return decision.allowed
    except (OSError, ValueError, KeyError, TypeError):
        return False

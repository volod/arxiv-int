"""Activation requires global checks and exact-generation model success."""

from arxiv_int.interfaces.stores import TransformationRunRef, ValidationResultRef
from arxiv_int.pipeline.control.quality import QualityCheck, activation_decision
from tests.pipeline.control.identities import passing_checks


def test_warnings_quarantine_but_do_not_block() -> None:
    decision = activation_decision(
        (
            QualityCheck("global.row_count", "pass", "global", "error", True),
            QualityCheck("batch.nulls", "warning", "batch", "warning", True),
        ),
        generation_id="gen-1",
    )
    assert decision.allowed
    assert decision.quarantined
    assert decision.warnings == ("batch.nulls",)


def test_missing_global_or_not_run_required_checks_block() -> None:
    missing_global = activation_decision(
        (QualityCheck("batch.not_null", "pass", "batch", "error", True),),
        generation_id="gen-1",
    )
    assert not missing_global.allowed
    assert "missing global quality checks" in missing_global.blocking
    not_run = activation_decision(
        (QualityCheck("global.row_count", "not-run", "global", "error", True),),
        generation_id="gen-1",
    )
    assert not not_run.allowed


def test_transform_and_validation_must_match_generation() -> None:
    decision = activation_decision(
        passing_checks(),
        validations=(ValidationResultRef("documents", "gen-other", "cat", "ok", True),),
        transformations=(
            TransformationRunRef("run-1", "gen-1", "build", "ok", "in", "model", True),
        ),
        generation_id="gen-1",
    )
    assert not decision.allowed
    assert any("validation generation" in item for item in decision.blocking)

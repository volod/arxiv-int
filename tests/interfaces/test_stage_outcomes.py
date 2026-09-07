from pathlib import Path

from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.interfaces.stores import DatasetRef, ValidationResultRef


def _context() -> StageContext:
    return StageContext(
        stage="facts",
        run_id="run-1",
        generation_id="gen-1",
        silos=(SiloRoot("alpha", Path("/silos/alpha")),),
        results_dir=Path("/results"),
        options={},
    )


def test_partial_outcome_carries_incomplete_outputs_and_failed_validation() -> None:
    result = StageResult(
        stage="facts",
        outcome="partial",
        detail="extractor timed out after 12 of 40 shards",
        outputs=(
            DatasetRef(
                dataset="facts",
                contract_version="1.0.0",
                generation_id="gen-1",
                partition={"bucket": "aa"},
            ),
        ),
        validations=(
            ValidationResultRef(
                contract_id="urn:arxiv-int:contract:facts:1.0.0",
                generation_id="gen-1",
                catalog_fingerprint="sha256:catalog",
                status="fail",
                publishable=False,
            ),
        ),
    )

    assert result.outcome == "partial"
    assert result.outputs
    assert result.validations[0].publishable is False


def test_empty_outcome_is_a_valid_negative_result() -> None:
    result = StageResult(stage="facts", outcome="empty", detail="no proposed facts in this shard")

    assert result.outcome == "empty"
    assert result.outputs == ()


def test_not_selected_outcome_records_the_missing_optional_branch() -> None:
    result = StageResult(
        stage="embed",
        outcome="not-selected",
        detail="gpu feature was not selected; lexical baseline remains active",
    )

    assert result.outcome == "not-selected"
    assert "gpu" in result.detail


def test_failed_outcome_does_not_publish_outputs() -> None:
    result = StageResult(stage="extract", outcome="failed", detail="tika endpoint refused")

    assert result.outcome == "failed"
    assert result.outputs == ()
    assert _context().generation_id == "gen-1"

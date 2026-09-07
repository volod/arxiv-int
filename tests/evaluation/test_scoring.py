import pytest

from arxiv_int.data_quality.model import (
    STATUS_PASS,
    VALIDATION_DEPTH_DATA,
    DatasetValidationResult,
    ToolFingerprint,
    ValidationLimits,
)
from arxiv_int.evaluation.accuracy import percentile, score_classification, score_extraction_item
from arxiv_int.evaluation.anomaly_eval import review_budget_precision, score_anomaly
from arxiv_int.evaluation.eval_errors import MissingEvidenceError
from arxiv_int.evaluation.fixture_kinds import (
    DATA_CLASS_RAW,
    DATA_CLASS_TRANSFORMED,
    METRIC_CLASS_HELD_OUT,
    METRIC_CLASS_STRUCTURAL,
)
from arxiv_int.evaluation.geo_eval import score_geotemporal, score_ontology
from arxiv_int.evaluation.scoring import (
    metric_class_for,
    refuse_empty_metrics,
    structural_is_not_accuracy,
)


def test_extraction_and_hierarchy_have_positive_and_negative_cases() -> None:
    gold = {
        "anchors": [{"document_id": "d", "end": 4, "start": 0}],
        "expected": ["alpha"],
        "failure": None,
    }
    good = score_extraction_item(gold, {"predicted": ["alpha"], "spans": gold["anchors"]})
    bad = score_extraction_item(gold, {"predicted": ["beta"], "spans": []})
    assert good["extraction_f1"] == 1.0
    assert good["span_f1"] == 1.0
    assert bad["extraction_f1"] == 0.0
    path = {"path": ["6", "62"], "primary": "62"}
    exact = score_classification(path, path)
    wrong = score_classification(path, {"path": ["5"], "primary": "5"})
    exceptional = score_classification(
        {"path": ["unclassified"], "primary": "unclassified"},
        {"path": ["6"], "primary": "6"},
    )
    assert exact.exact == 1.0
    assert wrong.exact == 0.0
    assert exceptional.exceptional == 0.0


def test_p95_and_empty_metrics_refuse_missing_evidence() -> None:
    assert percentile((1.0, 2.0, 3.0, 4.0), 50.0) == 2.0
    with pytest.raises(MissingEvidenceError):
        percentile(())
    with pytest.raises(MissingEvidenceError):
        refuse_empty_metrics({})
    with pytest.raises(MissingEvidenceError, match="not finite"):
        refuse_empty_metrics({"latency_p95_ms": float("nan")})
    with pytest.raises(MissingEvidenceError, match="not finite"):
        refuse_empty_metrics({"recall_at_k": float("inf")})


def test_ontology_and_geotemporal_negatives_do_not_collapse() -> None:
    add = {"action": "add", "change": "additive", "term_id": "pred.x"}
    assert score_ontology(add, add)["change_match"] == 1.0
    assert score_ontology(add, {**add, "change": "breaking"})["change_match"] == 0.0
    draft = {"action": "draft", "allowed": False, "term_id": "pred.d"}
    assert score_ontology(draft, {**draft, "allowed": True})["draft_refused"] == 0.0
    geo = {
        "recorded_time": "2021-06-01",
        "source_valid_start": "2019-01-01",
        "unknown_crs": True,
        "crs": None,
    }
    collapsed = score_geotemporal(
        geo, {**geo, "source_valid_start": "2021-06-01", "crs": "EPSG:4326", "unknown_crs": False}
    )
    assert collapsed["source_recorded_distinct"] == 0.0
    assert collapsed["unknown_crs_kept"] == 0.0
    kept = score_geotemporal(geo, geo)
    assert kept["source_recorded_distinct"] == 1.0
    assert kept["unknown_crs_kept"] == 1.0


def test_structural_quality_is_not_held_out_accuracy() -> None:
    result = DatasetValidationResult(
        contract_id="evaluation-items",
        status=STATUS_PASS,
        validation_depth=VALIDATION_DEPTH_DATA,
        publishable=True,
        checked_rows=1,
        input_fingerprint="a" * 64,
        catalog_fingerprint="b" * 64,
        tool_fingerprint=ToolFingerprint({}),
        checks=(),
        missing_required=(),
        limits=ValidationLimits(),
    )
    assert structural_is_not_accuracy(result) == METRIC_CLASS_STRUCTURAL
    assert metric_class_for(data_class=DATA_CLASS_RAW, held_out=True) == METRIC_CLASS_HELD_OUT
    assert (
        metric_class_for(data_class=DATA_CLASS_TRANSFORMED, held_out=False)
        == METRIC_CLASS_STRUCTURAL
    )


def test_anomaly_false_positives_and_review_budget() -> None:
    gold = {
        "cohort": "hard-negative",
        "flagged": False,
        "review_needed": False,
        "time_leakage": False,
    }
    fp = score_anomaly(gold, {**gold, "flagged": True, "review_needed": True})
    tn = score_anomaly(gold, gold)
    assert fp.false_positive == 1.0
    assert tn.false_positive == 0.0
    leak = score_anomaly(
        {"cohort": "time-leakage", "flagged": False, "time_leakage": True, "valid": False},
        {"flagged": True, "time_leakage": False, "valid": True},
    )
    assert leak.leakage_refused == 0.0
    precision = review_budget_precision((tn, tn))
    assert precision == 1.0

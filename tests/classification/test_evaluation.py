"""Frozen held-out classification metric and gate tests."""

from arxiv_int.classification.evaluation import evaluate
from arxiv_int.classification.policy import load_classifier_policy


def _label(item: str, primary: str, path: list[str]) -> dict[str, object]:
    return {"item_id": item, "path": path, "primary": primary, "split": "test"}


def _prediction(
    item: str, primary: str, path: list[str], confidence: float = 1.0
) -> dict[str, object]:
    return {
        "ancestor_path": ">".join(path),
        "confidence": confidence,
        "occurrence_id": item,
        "primary_class_id": primary,
        "alternate_class_ids_json": "[]",
    }


def _manifest() -> dict[str, object]:
    return {
        "reproducibility": {"checked_rows": 4, "status": "pass"},
        "runtime": {"peak_memory_mib": 64.0, "throughput_files_per_second": 100.0},
    }


def test_perfect_held_out_set_passes_every_predeclared_gate() -> None:
    labels = [
        _label("one", "tax:02.03.01", ["tax:02", "tax:02.03", "tax:02.03.01"]),
        _label("two", "tax:04.02.01", ["tax:04", "tax:04.02", "tax:04.02.01"]),
        _label("three", "unclassified", ["unclassified"]),
        _label("four", "unreadable", ["unreadable"]),
    ]
    predictions = [
        _prediction(str(row["item_id"]), str(row["primary"]), list(row["path"])) for row in labels
    ]

    report = evaluate(labels, predictions, _manifest(), load_classifier_policy())

    assert report.passed
    assert report.metrics["exact_accuracy"] == 1.0
    assert report.metrics["exact_precision"] == 1.0
    assert report.metrics["exact_recall"] == 1.0
    assert report.metrics["exceptional"]["macro_f1"] == 1.0
    assert report.metrics["mean_hierarchical_distance"] == 0.0
    assert report.metrics["selective_coverage"][-1]["accuracy"] == 1.0


def test_missing_prediction_is_a_blocking_accounting_error() -> None:
    labels = [_label("missing", "unclassified", ["unclassified"])]

    try:
        evaluate(labels, [], _manifest(), load_classifier_policy())
    except ValueError as error:
        assert "miss 1 frozen label" in str(error)
    else:
        raise AssertionError("missing held-out prediction was accepted")


def test_wrong_leaf_reports_ancestor_credit_distance_and_failed_gates() -> None:
    labels = [_label("one", "tax:04.02.01", ["tax:04", "tax:04.02", "tax:04.02.01"])]
    predictions = [_prediction("one", "tax:04.02.02", ["tax:04", "tax:04.02", "tax:04.02.02"], 0.9)]

    report = evaluate(labels, predictions, _manifest(), load_classifier_policy())

    assert not report.passed
    assert report.metrics["exact_accuracy"] == 0.0
    assert report.metrics["hierarchical_precision"] == 2 / 3
    assert report.metrics["mean_hierarchical_distance"] == 2.0


def test_exact_precision_and_recall_include_alternate_labels() -> None:
    label = _label("one", "tax:02.03.01", ["tax:02", "tax:02.03", "tax:02.03.01"])
    label["alternates"] = ["tax:04.02.01"]
    prediction = _prediction("one", "tax:02.03.01", ["tax:02", "tax:02.03", "tax:02.03.01"])
    prediction["alternate_class_ids_json"] = '["tax:03.01.01"]'

    report = evaluate([label], [prediction], _manifest(), load_classifier_policy())

    assert report.metrics["exact_precision"] == 0.5
    assert report.metrics["exact_recall"] == 0.5
    assert report.metrics["exact_f1"] == 0.5

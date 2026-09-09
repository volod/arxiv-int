import pytest

from arxiv_int.evaluation.scoring.linkage import LinkageLabel, score_linkage


def test_linkage_metrics_score_unordered_pairs_at_the_recorded_threshold() -> None:
    labels = [
        LinkageLabel("a", "b", True),
        LinkageLabel("a", "c", False),
        LinkageLabel("b", "c", True),
        LinkageLabel("c", "d", False),
    ]

    metrics = score_linkage([("b", "a"), ("a", "c")], labels, threshold=0.9)

    assert metrics.threshold == 0.9
    assert (metrics.true_positives, metrics.false_positives) == (1, 1)
    assert (metrics.true_negatives, metrics.false_negatives) == (1, 1)
    assert metrics.precision == metrics.recall == metrics.f1 == 0.5


def test_linkage_metrics_reject_ambiguous_label_ledgers() -> None:
    duplicate = [LinkageLabel("a", "b", True), LinkageLabel("b", "a", False)]

    with pytest.raises(ValueError, match="duplicate linkage label"):
        score_linkage([], duplicate, threshold=0.5)

    with pytest.raises(ValueError, match="two different records"):
        score_linkage([("a", "a")], [], threshold=0.5)

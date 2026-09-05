import pytest

from arxiv_int.evaluation.paired import paired_comparison, paired_verdict


def test_paired_comparison_is_seeded_and_keeps_the_item_ledger() -> None:
    candidate = [1.0, 0.8, 0.7, 0.9, 0.6, 0.5]
    baseline = [0.5, 0.4, 0.3, 0.2, 0.1, 0.0]

    first = paired_comparison(candidate, baseline, resamples=100, seed=7)
    second = paired_comparison(candidate, baseline, resamples=100, seed=7)

    assert first == second
    assert (first.wins, first.losses, first.ties) == (6, 0, 0)
    assert first.sign_test_p == 0.03125
    assert paired_verdict(first) == "adopt"


def test_paired_verdict_can_retain_the_baseline() -> None:
    comparison = paired_comparison([0.0] * 6, [1.0] * 6, resamples=50)

    assert paired_verdict(comparison) == "retain baseline"


def test_paired_verdict_does_not_overstate_too_few_pairs() -> None:
    comparison = paired_comparison([1.0] * 5, [0.0] * 5, resamples=50)

    assert comparison.delta.low > 0.0
    assert paired_verdict(comparison) == "inconclusive"


def test_paired_comparison_rejects_missing_or_unaligned_evidence() -> None:
    with pytest.raises(ValueError, match="at least one"):
        paired_comparison([], [])
    with pytest.raises(ValueError, match="one baseline"):
        paired_comparison([1.0], [])

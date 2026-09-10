"""Second-opinion scoring and the preregistered adopt/retain/inconclusive rule."""

from arxiv_int.evaluation.scoring.paired import paired_comparison, paired_verdict
from arxiv_int.retrieval.second_opinion.decision import (
    VERDICT_ADOPT,
    VERDICT_INCONCLUSIVE,
    VERDICT_RETAIN,
    verdict_for,
)
from arxiv_int.retrieval.second_opinion.model import (
    CaseRun,
    DecisionPolicy,
    Endpoint,
    SplitCase,
    SplitChunk,
)
from arxiv_int.retrieval.second_opinion.scoring import ndcg, score_case

POLICY = DecisionPolicy(1.0, 50.0, 2.0, 5.0, 20, 0, 0.02, 0, 0)
PASS = {"identifier_exactness": True, "latency_p95": True}
CHUNKS = {
    name: SplitChunk(name, "d1", "t", "body text", name, "rus", start, start + 9)
    for name, start in (("r1", 0), ("r2", 11), ("n1", 22), ("f1", 33))
}


def _endpoint(name: str, candidate: list[float], baseline: list[float]) -> Endpoint:
    paired = paired_comparison(candidate, baseline, resamples=500, seed=13)
    return Endpoint(name, "metric", "c", "b", len(candidate), paired, paired_verdict(paired))


def _run(hits: tuple[str, ...], error: str = "") -> CaseRun:
    return CaseRun("c", "case", hits, "primary", error, (1.0,), True)


def test_ndcg_rewards_rank_and_multiple_relevant_chunks() -> None:
    assert ndcg(("r1", "r2"), {"r1", "r2"}, 10) == 1.0
    assert 0.0 < ndcg(("n1", "r1"), {"r1"}, 10) < 1.0
    assert ndcg((), {"r1"}, 10) == 0.0
    assert ndcg((), set(), 10) == 1.0
    assert ndcg(("n1",), set(), 10) == 0.0


def test_score_counts_precision_false_positives_and_forbidden_hits() -> None:
    case = SplitCase("case", "multi_term", "match", "q", ("r1",), ("n1",), ("f1",))
    score = score_case(case, _run(("r1", "n1", "f1")), CHUNKS, k_quality=10, k_precision=5)
    assert score.precision == 1 / 3 and score.hard_negatives == 1 and score.forbidden_hits == 1
    assert score.recall == 1.0 and score.reciprocal_rank == 1.0 and score.intact == 1.0
    empty = score_case(case, _run(()), CHUNKS, k_quality=10, k_precision=5)
    assert empty.precision == 1.0 and empty.recall == 0.0 and not empty.false_positive
    no_answer = SplitCase("case", "mixed_script_fp", "match", "most", (), ("n1",), ())
    assert score_case(no_answer, _run(("n1",)), CHUNKS, k_quality=10, k_precision=5).false_positive
    assert score_case(no_answer, _run(()), CHUNKS, k_quality=10, k_precision=5).exact


def test_a_sibling_chunk_of_the_relevant_document_is_not_intact() -> None:
    case = SplitCase("case", "inflection", "match", "q", ("r1",), (), ())
    assert score_case(case, _run(("r2",)), CHUNKS, k_quality=10, k_precision=5).intact == 0.0


def test_gate_failure_or_significant_regression_retains_the_baseline() -> None:
    better = _endpoint("quality", [1.0] * 25, [0.0] * 25)
    worse = _endpoint("precision", [0.0] * 25, [1.0] * 25)
    level = _endpoint("precision", [1.0] * 25, [1.0] * 25)
    assert verdict_for(POLICY, better, level, {**PASS, "latency_p95": False})[0] == VERDICT_RETAIN
    assert verdict_for(POLICY, better, worse, PASS)[0] == VERDICT_RETAIN


def test_adopt_needs_enough_decided_pairs_and_a_non_inferior_other_endpoint() -> None:
    level = _endpoint("precision", [1.0] * 30, [1.0] * 30)
    assert (
        verdict_for(POLICY, _endpoint("quality", [1.0] * 25, [0.0] * 25), level, PASS)[0]
        == VERDICT_ADOPT
    )
    few = _endpoint("quality", [1.0] * 8 + [0.5] * 22, [0.0] * 8 + [0.5] * 22)
    assert verdict_for(POLICY, few, level, PASS) == (
        VERDICT_INCONCLUSIVE,
        ("quality improved on 8 decided pairs",),
    )
    precise = _endpoint("precision", [1.0] * 22 + [0.5] * 8, [0.0] * 22 + [0.5] * 8)
    flat = _endpoint("quality", [0.5] * 30, [0.5] * 30)
    assert verdict_for(POLICY, flat, precise, PASS)[0] == VERDICT_ADOPT


def test_no_significant_difference_is_inconclusive() -> None:
    mixed = _endpoint("quality", [1.0, 0.0] * 15, [0.0, 1.0] * 15)
    level = _endpoint("precision", [1.0] * 30, [1.0] * 30)
    assert verdict_for(POLICY, mixed, level, PASS)[0] == VERDICT_INCONCLUSIVE

"""Paired endpoints, mandatory gates, and the preregistered adopt/retain/inconclusive rule."""

from collections.abc import Mapping, Sequence

from arxiv_int.evaluation.scoring.accuracy import percentile
from arxiv_int.evaluation.scoring.paired import paired_comparison, paired_verdict
from arxiv_int.retrieval.second_opinion.model import (
    MODE_IDENTIFIER,
    MODE_MATCH,
    CaseRun,
    CaseScore,
    Decision,
    DecisionPolicy,
    Endpoint,
    Protocol,
    SplitCase,
    SplitData,
)
from arxiv_int.retrieval.second_opinion.scoring import mean

VERDICT_ADOPT = "adopt"
VERDICT_RETAIN = "retain baseline"
VERDICT_INCONCLUSIVE = "inconclusive"
QUALITY_FIELD = "ndcg"
PRECISION_FIELD = "precision"
Scores = Mapping[tuple[str, str], CaseScore]


def cohort_cases(protocol: Protocol, split: SplitData, group: str) -> tuple[SplitCase, ...]:
    """Return the split cases of one declared cohort group in their served mode."""
    names = set(protocol.cohorts[group])
    mode = MODE_IDENTIFIER if group == "gate_identifier" else MODE_MATCH
    return tuple(case for case in split.cases if case.cohort in names and case.mode == mode)


def endpoint(
    protocol: Protocol,
    split: SplitData,
    scores: Scores,
    *,
    name: str,
    group: str,
    field: str,
    candidate: str,
    baseline: str,
    seed: int,
) -> Endpoint:
    """Pair one metric over one cohort group for two arms."""
    cases = cohort_cases(protocol, split, group)
    paired = paired_comparison(
        [float(getattr(scores[(candidate, case.case_id)], field)) for case in cases],
        [float(getattr(scores[(baseline, case.case_id)], field)) for case in cases],
        confidence=protocol.confidence,
        resamples=protocol.resamples,
        seed=seed,
    )
    return Endpoint(name, field, candidate, baseline, len(cases), paired, paired_verdict(paired))


def latency_p95(runs: Sequence[CaseRun], arm_id: str) -> float:
    """Return one arm's nearest-rank p95 over every successful repeated sample."""
    samples = [value for run in runs if run.arm_id == arm_id for value in run.latencies_ms]
    return percentile(samples) if samples else 0.0


def gates(
    protocol: Protocol, split: SplitData, runs: Sequence[CaseRun], scores: Scores
) -> dict[str, bool]:
    """Evaluate every preregistered mandatory gate for the candidate arm."""
    policy = protocol.decision
    candidate, baseline = protocol.candidate, protocol.baseline
    by_run = {(run.arm_id, run.case_id): run for run in runs}
    identifier = cohort_cases(protocol, split, "gate_identifier")
    syntax = cohort_cases(protocol, split, "gate_syntax")
    no_answer = cohort_cases(protocol, split, "no_answer")
    new_errors = sum(
        1
        for case in syntax
        if by_run[(candidate, case.case_id)].error and not by_run[(baseline, case.case_id)].error
    )
    false_positives = sum(scores[(candidate, case.case_id)].false_positive for case in no_answer)
    baseline_false_positives = sum(
        scores[(baseline, case.case_id)].false_positive for case in no_answer
    )
    candidate_p95, baseline_p95 = latency_p95(runs, candidate), latency_p95(runs, baseline)
    relative = (
        candidate_p95 <= policy.latency_p95_ratio_max * baseline_p95
        or candidate_p95 - baseline_p95 <= policy.latency_p95_increase_ms_max
    )
    return {
        "identifier_exactness": (
            mean(float(scores[(candidate, case.case_id)].exact) for case in identifier)
            if identifier
            else 1.0
        )
        >= policy.identifier_exactness,
        "latency_p95": candidate_p95 <= policy.latency_p95_ms_max and relative,
        "no_answer_false_positives": false_positives - baseline_false_positives
        <= policy.no_answer_false_positive_increase_max,
        "syntax_forbidden_hits": sum(
            scores[(candidate, case.case_id)].forbidden_hits for case in syntax
        )
        <= policy.syntax_forbidden_hits_max,
        "syntax_new_errors": new_errors <= policy.syntax_new_errors_max,
    }


def decide(
    protocol: Protocol, split: SplitData, runs: Sequence[CaseRun], scores: Scores
) -> Decision:
    """Apply the preregistered rule, then the seed and repetition stability overrides."""
    results = gates(protocol, split, runs, scores)
    quality, precision = _endpoints(protocol, split, scores, protocol.primary_seed)
    verdict, reasons = verdict_for(protocol.decision, quality, precision, results)
    seeds = {
        seed: verdict_for(protocol.decision, *_endpoints(protocol, split, scores, seed), results)[0]
        for seed in protocol.sensitivity_seeds
    }
    stable = all(
        run.stable for run in runs if run.arm_id in {protocol.candidate, protocol.baseline}
    )
    if len(set(seeds.values())) > 1:
        verdict, reasons = VERDICT_INCONCLUSIVE, (*reasons, "bootstrap seed changed the verdict")
    if not stable:
        verdict, reasons = (
            VERDICT_INCONCLUSIVE,
            (*reasons, "ranked hits changed across repetitions"),
        )
    return Decision(verdict, reasons, results, quality, precision, seeds, stable)


def verdict_for(
    policy: DecisionPolicy, quality: Endpoint, precision: Endpoint, results: Mapping[str, bool]
) -> tuple[str, tuple[str, ...]]:
    """Return the preregistered verdict for one pair of endpoints and gate results."""
    failed = sorted(name for name, passed in results.items() if not passed)
    if failed:
        return VERDICT_RETAIN, (f"mandatory gate failed: {', '.join(failed)}",)
    if VERDICT_RETAIN in {quality.verdict, precision.verdict}:
        return VERDICT_RETAIN, ("a paired endpoint regressed significantly",)
    margin = -policy.non_inferiority_margin
    for improved, other in ((quality, precision), (precision, quality)):
        decided = improved.paired.wins + improved.paired.losses
        if improved.verdict == VERDICT_ADOPT and other.paired.delta.low >= margin:
            if decided >= policy.min_decided_pairs:
                return VERDICT_ADOPT, (f"{improved.name} improved; {other.name} non-inferior",)
            return VERDICT_INCONCLUSIVE, (f"{improved.name} improved on {decided} decided pairs",)
    return VERDICT_INCONCLUSIVE, ("no endpoint met the preregistered adopt rule",)


def comparisons(protocol: Protocol, split: SplitData, scores: Scores) -> tuple[Endpoint, ...]:
    """Return quality and precision endpoints for every declared factor comparison."""
    compared: list[Endpoint] = []
    for item in protocol.comparisons:
        for group, field in (("quality", QUALITY_FIELD), ("precision", PRECISION_FIELD)):
            compared.append(
                endpoint(
                    protocol,
                    split,
                    scores,
                    name=f"{item.name}:{group}",
                    group=group,
                    field=field,
                    candidate=item.candidate,
                    baseline=item.baseline,
                    seed=protocol.primary_seed,
                )
            )
    return tuple(compared)


def _endpoints(
    protocol: Protocol, split: SplitData, scores: Scores, seed: int
) -> tuple[Endpoint, Endpoint]:
    return tuple(  # type: ignore[return-value]
        endpoint(
            protocol,
            split,
            scores,
            name=group,
            group=group,
            field=field,
            candidate=protocol.candidate,
            baseline=protocol.baseline,
            seed=seed,
        )
        for group, field in (("quality", QUALITY_FIELD), ("precision", PRECISION_FIELD))
    )

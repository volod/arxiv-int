"""Arm summaries, the case ledger, and the detailed report of one execution."""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from statistics import median

from arxiv_int.evaluation.scoring.accuracy import percentile
from arxiv_int.retrieval.second_opinion.decision import cohort_cases
from arxiv_int.retrieval.second_opinion.model import (
    CaseScore,
    Decision,
    Endpoint,
    Execution,
    Protocol,
    SplitCase,
)
from arxiv_int.retrieval.second_opinion.scoring import mean

MEDIAN_PERCENTILE = 50.0


def arm_summary(protocol: Protocol, execution: Execution, arm_id: str) -> dict[str, object]:
    """Aggregate one arm's quality, precision, gate, and latency readings."""
    scores = {score.case_id: score for score in execution.scores if score.arm_id == arm_id}
    runs = [run for run in execution.runs if run.arm_id == arm_id]
    quality = cohort_cases(protocol, execution.split, "quality")
    precision = cohort_cases(protocol, execution.split, "precision")
    no_answer = cohort_cases(protocol, execution.split, "no_answer")
    return {
        "arm": arm_id,
        "cohort_ndcg": _cohort_ndcg(scores, quality),
        "errors": sum(1 for run in runs if run.error),
        "latency_ms": _latency([value for run in runs for value in run.latencies_ms]),
        "no_answer_false_positives": sum(scores[case.case_id].false_positive for case in no_answer),
        "precision": {
            "cases": len(precision),
            "hard_negatives_at_k": _total(scores, precision, "hard_negatives"),
            "returned_precision": _average(scores, precision, "precision"),
            "unjudged_at_k": _total(scores, precision, "unjudged"),
        },
        "quality": {
            "cases": len(quality),
            "intact": _average(scores, quality, "intact"),
            "mrr": _average(scores, quality, "reciprocal_rank"),
            "ndcg": _average(scores, quality, "ndcg"),
            "recall": _average(scores, quality, "recall"),
        },
        "stages": dict(sorted(Counter(run.stage for run in runs).items())),
        "unstable_cases": sum(1 for run in runs if not run.stable),
    }


def _average(scores: Mapping[str, CaseScore], cases: Sequence[SplitCase], field: str) -> float:
    return round(mean(float(getattr(scores[case.case_id], field)) for case in cases), 4)


def _total(scores: Mapping[str, CaseScore], cases: Sequence[SplitCase], field: str) -> int:
    return sum(int(getattr(scores[case.case_id], field)) for case in cases)


def _cohort_ndcg(scores: Mapping[str, CaseScore], cases: Sequence[SplitCase]) -> dict[str, float]:
    cohorts = sorted({case.cohort for case in cases})
    return {
        cohort: _average(scores, [case for case in cases if case.cohort == cohort], "ndcg")
        for cohort in cohorts
    }


def case_rows(execution: Execution) -> list[dict[str, object]]:
    """Return the canonical per-arm, per-case ledger rows."""
    runs = {(run.arm_id, run.case_id): run for run in execution.runs}
    rows = []
    for score in execution.scores:
        run = runs[(score.arm_id, score.case_id)]
        rows.append(
            {
                **asdict(score),
                "error": run.error,
                "hits": list(run.hits),
                "latency_median_ms": round(median(run.latencies_ms), 3)
                if run.latencies_ms
                else 0.0,
                "samples": len(run.latencies_ms),
                "stable": run.stable,
                "stage": run.stage,
            }
        )
    return rows


def report_payload(
    protocol: Protocol,
    execution: Execution,
    decision: Decision,
    compared: Sequence[Endpoint],
) -> dict[str, object]:
    """Return the detailed JSON report registered beside the ledger."""
    return {
        "arms": [arm_summary(protocol, execution, arm.arm_id) for arm in protocol.arms],
        "builds": [
            {
                **asdict(build),
                "median_seconds": round(median(build.build_seconds), 6),
            }
            for build in execution.builds
        ],
        "comparisons": [endpoint_payload(item) for item in compared],
        "decision": {
            "gates": decision.gates,
            "precision": endpoint_payload(decision.precision),
            "quality": endpoint_payload(decision.quality),
            "reasons": list(decision.reasons),
            "seed_verdicts": {
                str(seed): verdict for seed, verdict in decision.seed_verdicts.items()
            },
            "stable_hits": decision.stable_hits,
            "verdict": decision.verdict,
        },
        "execution": {
            "engine_version": execution.engine_version,
            "filler_rows": execution.filler_rows,
            "judged_chunks": len(execution.split.chunks),
            "repetitions": execution.repetitions,
            "split": execution.split.name,
        },
    }


def endpoint_payload(item: Endpoint) -> dict[str, object]:
    """Return one paired endpoint as JSON."""
    return {
        "baseline": item.baseline,
        "candidate": item.candidate,
        "decided": item.paired.wins + item.paired.losses,
        "delta": asdict(item.paired.delta),
        "items": item.items,
        "losses": item.paired.losses,
        "metric": item.metric,
        "name": item.name,
        "sign_test_p": item.paired.sign_test_p,
        "ties": item.paired.ties,
        "verdict": item.verdict,
        "wins": item.paired.wins,
    }


def manifest_metrics(protocol: Protocol, execution: Execution) -> dict[str, float]:
    """Return the flat headline metrics recorded in the manifest."""
    metrics: dict[str, float] = {}
    for arm in protocol.arms:
        summary = arm_summary(protocol, execution, arm.arm_id)
        quality, precision, latency = (
            summary["quality"],
            summary["precision"],
            summary["latency_ms"],
        )
        assert (
            isinstance(quality, dict) and isinstance(precision, dict) and isinstance(latency, dict)
        )
        metrics[f"{arm.arm_id}.ndcg_at_{protocol.k_quality}"] = float(quality["ndcg"])
        metrics[f"{arm.arm_id}.recall_at_{protocol.k_quality}"] = float(quality["recall"])
        metrics[f"{arm.arm_id}.returned_precision_at_{protocol.k_precision}"] = float(
            precision["returned_precision"]
        )
        metrics[f"{arm.arm_id}.p95_latency_ms"] = float(latency["p95"])
    for build in execution.builds:
        metrics[f"{build.index_profile}.build_median_seconds"] = round(
            median(build.build_seconds), 6
        )
        metrics[f"{build.index_profile}.index_bytes"] = float(build.index_bytes)
    return metrics


def _latency(samples: Sequence[float]) -> dict[str, float]:
    if not samples:
        return {"max": 0.0, "p50": 0.0, "p95": 0.0, "samples": 0.0}
    return {
        "max": round(max(samples), 3),
        "p50": round(percentile(samples, MEDIAN_PERCENTILE), 3),
        "p95": round(percentile(samples), 3),
        "samples": float(len(samples)),
    }

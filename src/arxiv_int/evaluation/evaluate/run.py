"""Run the evaluate stage against frozen fixtures and publish a run bundle."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.evaluation.bundles import BundleSpec, PublishedBundle, publish_run_bundle
from arxiv_int.evaluation.bundles.layout import digest_bytes
from arxiv_int.evaluation.bundles.manifest import canonical_json
from arxiv_int.evaluation.evaluate.errors import MissingEvidenceError
from arxiv_int.evaluation.evaluate.paths import evaluation_artifact_dir, published_evaluation_dir
from arxiv_int.evaluation.families import all_items, load_fixture_catalog
from arxiv_int.evaluation.fixtures.guard import item_ledger
from arxiv_int.evaluation.fixtures.kinds import (
    DATA_CLASS_RAW,
    DEFAULT_BOOTSTRAP_SEED,
    METRIC_CLASS_HELD_OUT,
    THRESHOLD_ADOPT,
)
from arxiv_int.evaluation.fixtures.model import EvaluationItem, ItemLedger
from arxiv_int.evaluation.scoring import comparison_verdict, polarity_scores, refuse_empty_metrics
from arxiv_int.evaluation.scoring.anomaly import resource_metrics, score_resource
from arxiv_int.evaluation.scoring.paired import paired_comparison


@dataclass(frozen=True, slots=True)
class EvaluateRequest:
    """Inputs for one fixture-backed evaluate run."""

    run_id: str
    project_root: Path
    fixture_root: Path
    runs_dir: Path
    seed: int = DEFAULT_BOOTSTRAP_SEED
    data_class: str = DATA_CLASS_RAW
    resource: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class EvaluateOutcome:
    """Published bundle plus the replayable ledger used to score it."""

    bundle: PublishedBundle
    ledger: ItemLedger
    metrics: Mapping[str, float]
    verdict: str
    diagnostics: Path


def code_fingerprint(project_root: Path) -> str:
    """Hash evaluation package sources so stale proofs can be detected."""
    root = project_root / "src" / "arxiv_int" / "evaluation"
    blobs = [path.read_bytes() for path in sorted(root.glob("*.py"))]
    return digest_bytes(b"".join(blobs))


def run_evaluate(request: EvaluateRequest) -> EvaluateOutcome:
    """Score frozen polarities and publish ``$RUNS_DIR/<run-id>/evaluation``."""
    items = all_items(load_fixture_catalog(request.fixture_root))
    ledger = item_ledger(items, seed=request.seed)
    rows, positives, negatives = _score_rows(items)
    metrics, verdict = _aggregate(positives, negatives, request.seed)
    if request.resource is not None:
        metrics = {**metrics, **resource_metrics(score_resource(request.resource))}
    bundle = publish_run_bundle(
        published_evaluation_dir(request.runs_dir, request.run_id),
        BundleSpec(
            run_id=request.run_id,
            kind="evaluate",
            input_fingerprints={
                "code": code_fingerprint(request.project_root),
                "fixtures": ledger.fingerprint,
            },
            configuration={
                "data_class": request.data_class,
                "metric_class": METRIC_CLASS_HELD_OUT,
                "seed": request.seed,
                "threshold_adopt": THRESHOLD_ADOPT,
            },
            metrics=metrics,
            verdict=verdict,
        ),
        rows,
        artifacts={"ledger.json": canonical_json(_ledger_payload(ledger)).decode("utf-8")},
    )
    diagnostics = evaluation_artifact_dir(request.project_root, request.run_id)
    diagnostics.mkdir(parents=True, exist_ok=True)
    (diagnostics / "summary.json").write_bytes(
        canonical_json(
            {
                "data_class": request.data_class,
                "fingerprint": bundle.fingerprint,
                "ledger": ledger.fingerprint,
                "metric_class": METRIC_CLASS_HELD_OUT,
                "run_id": request.run_id,
                "verdict": verdict,
            }
        )
    )
    return EvaluateOutcome(bundle, ledger, metrics, verdict, diagnostics)


def _score_rows(
    items: Sequence[EvaluationItem],
) -> tuple[list[dict[str, object]], list[float], list[float]]:
    rows: list[dict[str, object]] = []
    positives: list[float] = []
    negatives: list[float] = []
    for item in items:
        positive, negative = polarity_scores(item)
        positives.append(positive)
        negatives.append(negative)
        rows.append(
            {
                "gold_ref": item.gold_ref,
                "item_id": item.item_id,
                "item_kind": item.item_kind,
                "negative": negative,
                "positive": positive,
                "split": item.split,
            }
        )
    return rows, positives, negatives


def _aggregate(
    positives: Sequence[float], negatives: Sequence[float], seed: int
) -> tuple[dict[str, float], str]:
    if not positives or not negatives:
        raise MissingEvidenceError("evaluate needs positive and negative fixture scores")
    comparison = paired_comparison(positives, negatives, seed=seed)
    metrics = {
        "mean_negative": sum(negatives) / len(negatives),
        "mean_positive": sum(positives) / len(positives),
        "paired_delta": comparison.delta.mean,
        "paired_high": comparison.delta.high,
        "paired_low": comparison.delta.low,
        "sign_test_p": comparison.sign_test_p,
        "threshold_adopt": THRESHOLD_ADOPT,
    }
    refuse_empty_metrics(metrics)
    return metrics, comparison_verdict(comparison)


def _ledger_payload(ledger: ItemLedger) -> dict[str, object]:
    return {
        "family_counts": dict(ledger.family_counts),
        "fingerprint": ledger.fingerprint,
        "item_ids": list(ledger.item_ids),
        "seed": ledger.seed,
    }

"""Execute and publish one immutable Russian lexical calibration."""

import json
from dataclasses import asdict
from pathlib import Path

from sqlalchemy import create_engine

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.evaluation.bundles import BundleSpec, publish_run_bundle, verify_run_bundle
from arxiv_int.evaluation.scoring.paired import paired_comparison, paired_verdict
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.retrieval.calibration.config import load_calibration_config
from arxiv_int.retrieval.calibration.database import evaluate_profiles, paradedb_version
from arxiv_int.retrieval.calibration.model import (
    CalibrationConfig,
    CalibrationOutcome,
    ComparisonReading,
    ProfileReading,
)
from arxiv_int.retrieval.query_normalization import (
    SELECTED_QUERY_PROFILE,
    query_policy_fingerprint,
)
from arxiv_int.stores.projections.adapters.lexical import (
    SELECTED_INDEX_PROFILE,
    TOKENIZER_FINGERPRINT,
)

COMPARISONS = (
    ("russian-morphology", "unicode-russian-v1", "unicode-plain-v1"),
    ("query-normalization", "unicode-russian-safe-v1", "unicode-russian-v1"),
    ("icu-segmentation", "icu-russian-safe-v1", "unicode-russian-safe-v1"),
)


def run_calibration(
    *,
    project_root: Path,
    database_url: str,
    runs_dir: Path,
    run_id: str,
) -> CalibrationOutcome:
    """Build identical profile indexes, score the final split, and publish once."""
    if not run_id.strip() or run_id.strip() != run_id:
        raise ValueError("calibration run_id must be non-empty without surrounding whitespace")
    config = load_calibration_config(project_root)
    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                engine_version = paradedb_version(connection)
                readings = evaluate_profiles(
                    connection,
                    config,
                    run_token=sha256_text(run_id)[:10],
                )
            finally:
                transaction.rollback()
    finally:
        engine.dispose()
    comparisons = _comparisons(config, readings)
    decision = next(item for item in comparisons if item.name == "query-normalization")
    selected = config.candidate_profile if decision.verdict == "adopt" else config.baseline_profile
    selected_reading = _reading(readings, selected)
    baseline_reading = _reading(readings, config.baseline_profile)
    reindex = selected_reading.tokenizer_fingerprint != baseline_reading.tokenizer_fingerprint
    destination = runs_dir / run_id / "evaluation" / "lexical"
    published = publish_run_bundle(
        destination,
        BundleSpec(
            run_id=run_id,
            kind="lexical-retrieval",
            input_fingerprints={
                "calibration_config": config.fingerprint,
                "calibration_code": _code_fingerprint(project_root),
                "query_policy": query_policy_fingerprint(),
                "runtime_tokenizer": TOKENIZER_FINGERPRINT,
            },
            configuration={
                "baseline_profile": config.baseline_profile,
                "candidate_profile": config.candidate_profile,
                "confidence": config.confidence,
                "final_items": len(config.queries),
                "k": config.k,
                "paradedb_version": engine_version,
                "production_index_profile": SELECTED_INDEX_PROFILE,
                "production_query_profile": SELECTED_QUERY_PROFILE,
                "reindex_required": reindex,
                "resamples": config.resamples,
                "seed": config.seed,
                "selected_profile": selected,
            },
            metrics=_manifest_metrics(readings),
            verdict=decision.verdict,
        ),
        [row.as_json_dict() for reading in readings for row in reading.cases],
        artifacts={"profiles.json": normalize_json(_detail_payload(readings, comparisons))},
    )
    fingerprint = verify_run_bundle(published.directory)
    return CalibrationOutcome(
        verdict=decision.verdict,
        selected_profile=selected,
        reindex_required=reindex,
        bundle_dir=published.directory,
        manifest_fingerprint=fingerprint,
        engine_version=engine_version,
        readings=readings,
        comparisons=comparisons,
    )


def _comparisons(
    config: CalibrationConfig, readings: tuple[ProfileReading, ...]
) -> tuple[ComparisonReading, ...]:
    compared = []
    for name, candidate_id, baseline_id in COMPARISONS:
        candidate = _reading(readings, candidate_id)
        baseline = _reading(readings, baseline_id)
        paired = paired_comparison(
            [item.reciprocal_rank for item in candidate.cases],
            [item.reciprocal_rank for item in baseline.cases],
            confidence=config.confidence,
            resamples=config.resamples,
            seed=config.seed,
        )
        compared.append(
            ComparisonReading(name, candidate_id, baseline_id, paired, paired_verdict(paired))
        )
    return tuple(compared)


def _reading(readings: tuple[ProfileReading, ...], profile_id: str) -> ProfileReading:
    try:
        return next(item for item in readings if item.profile.profile_id == profile_id)
    except StopIteration as error:
        raise ValueError(f"calibration result is missing profile {profile_id!r}") from error


def _manifest_metrics(readings: tuple[ProfileReading, ...]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for reading in readings:
        prefix = reading.profile.profile_id.replace("-", "_")
        metrics.update(
            {
                f"{prefix}.build_seconds": reading.build_seconds,
                f"{prefix}.index_bytes": float(reading.index_bytes),
                f"{prefix}.mrr": reading.metrics.mean_reciprocal_rank,
                f"{prefix}.p95_latency_ms": reading.p95_latency_ms,
                f"{prefix}.recall_at_k": reading.metrics.recall_at_k,
                f"{prefix}.span_intact_at_k": reading.metrics.span_intact_at_k,
                f"{prefix}.table_bytes": float(reading.table_bytes),
            }
        )
    return metrics


def _detail_payload(
    readings: tuple[ProfileReading, ...], comparisons: tuple[ComparisonReading, ...]
) -> dict[str, object]:
    return {
        "comparisons": [
            {
                "baseline": item.baseline,
                "candidate": item.candidate,
                "confidence": item.paired.confidence,
                "delta": asdict(item.paired.delta),
                "losses": item.paired.losses,
                "name": item.name,
                "resamples": item.paired.resamples,
                "seed": item.paired.seed,
                "sign_test_p": item.paired.sign_test_p,
                "ties": item.paired.ties,
                "verdict": item.verdict,
                "wins": item.paired.wins,
            }
            for item in comparisons
        ],
        "profiles": [_profile_payload(item) for item in readings],
    }


def _profile_payload(reading: ProfileReading) -> dict[str, object]:
    metrics = reading.metrics
    return {
        "build_seconds": reading.build_seconds,
        "index_bytes": reading.index_bytes,
        "metrics": asdict(metrics),
        "p95_latency_ms": reading.p95_latency_ms,
        "profile_id": reading.profile.profile_id,
        "query_profile": reading.profile.query_profile,
        "table_bytes": reading.table_bytes,
        "text_tokenizer": reading.profile.text_tokenizer,
        "tokenizer_fingerprint": reading.tokenizer_fingerprint,
    }


def _code_fingerprint(project_root: Path) -> str:
    relative = (
        "src/arxiv_int/evaluation/bundles/__init__.py",
        "src/arxiv_int/evaluation/bundles/manifest.py",
        "src/arxiv_int/evaluation/scoring/accuracy.py",
        "src/arxiv_int/evaluation/scoring/paired.py",
        "src/arxiv_int/retrieval/calibration/config.py",
        "src/arxiv_int/retrieval/calibration/database.py",
        "src/arxiv_int/retrieval/calibration/model.py",
        "src/arxiv_int/retrieval/calibration/run.py",
        "src/arxiv_int/retrieval/lexical.py",
        "src/arxiv_int/retrieval/metrics.py",
        "src/arxiv_int/retrieval/projection.py",
        "src/arxiv_int/retrieval/query_normalization.py",
        "src/arxiv_int/stores/projections/adapters/lexical.py",
        "src/arxiv_int/stores/projections/adapters/lexical_search.py",
    )
    fingerprints = [hash_file(project_root / name)[0] for name in relative]
    return sha256_text(json.dumps(fingerprints, ensure_ascii=True, sort_keys=True))

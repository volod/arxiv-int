"""Immutable development, preregistration, and final second-opinion bundles."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.evaluation.bundles import (
    BundleSpec,
    PublishedBundle,
    publish_run_bundle,
    verify_run_bundle,
)
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.retrieval.query_normalization import query_policy_fingerprint
from arxiv_int.retrieval.second_opinion.model import (
    Decision,
    Endpoint,
    Execution,
    Protocol,
    SplitData,
)
from arxiv_int.retrieval.second_opinion.report import case_rows, manifest_metrics, report_payload
from arxiv_int.retrieval.second_opinion.splits import FrozenInputError, second_opinion_path
from arxiv_int.stores.projections.adapters.lexical import TOKENIZER_FINGERPRINT

BUNDLE_ROOT = "lexical-second-opinion"
KIND = "lexical-second-opinion"
STAGE_PREREGISTRATION = "preregistration"
_CODE_ROOT = Path("src/arxiv_int")
CODE_FILES = (
    "evaluation/bundles/__init__.py",
    "evaluation/bundles/manifest.py",
    "evaluation/scoring/accuracy.py",
    "evaluation/scoring/paired.py",
    "retrieval/lexical.py",
    "retrieval/lexical_model.py",
    "retrieval/metrics.py",
    "retrieval/projection.py",
    "retrieval/query_aliases.py",
    "retrieval/query_normalization.py",
    "retrieval/query_transforms.py",
    "retrieval/second_opinion/database.py",
    "retrieval/second_opinion/decision.py",
    "retrieval/second_opinion/filler.py",
    "retrieval/second_opinion/model.py",
    "retrieval/second_opinion/protocol.py",
    "retrieval/second_opinion/publish.py",
    "retrieval/second_opinion/report.py",
    "retrieval/second_opinion/run.py",
    "retrieval/second_opinion/scoring.py",
    "retrieval/second_opinion/splits.py",
    "stores/projections/adapters/lexical.py",
    "stores/projections/adapters/lexical_search.py",
)


def stage_directory(runs_dir: Path, run_id: str, stage: str) -> Path:
    """Return the immutable bundle directory for one run stage."""
    return runs_dir / run_id / "evaluation" / BUNDLE_ROOT / stage


def code_fingerprint(project_root: Path) -> str:
    """Hash every module that can change a second-opinion reading."""
    digests = [hash_file(project_root / _CODE_ROOT / name)[0] for name in CODE_FILES]
    return sha256_text(json.dumps(digests, ensure_ascii=True, sort_keys=True))


def input_fingerprints(project_root: Path, protocol: Protocol, split: str) -> dict[str, str]:
    """Return every frozen input, code, and runtime fingerprint for one split."""
    return {
        "arms": protocol.arms_fingerprint,
        "code": code_fingerprint(project_root),
        "filler": protocol.split_fingerprints["filler"],
        "protocol": protocol.fingerprint,
        "query_policy": query_policy_fingerprint(),
        "review_packet": hash_file(second_opinion_path(project_root, "review.json"))[0],
        "runtime_tokenizer": TOKENIZER_FINGERPRINT,
        f"{split}_split": protocol.split_fingerprints[split],
    }


def publish_preregistration(
    project_root: Path, runs_dir: Path, run_id: str, protocol: Protocol, final: SplitData
) -> PublishedBundle:
    """Bind the final split, thresholds, arms, policy, and code before final execution."""
    rows = [{"case_id": c.case_id, "cohort": c.cohort, "mode": c.mode} for c in final.cases]
    return publish_run_bundle(
        stage_directory(runs_dir, run_id, STAGE_PREREGISTRATION),
        BundleSpec(
            run_id=run_id,
            kind=f"{KIND}-preregistration",
            input_fingerprints=input_fingerprints(project_root, protocol, final.name),
            configuration=_configuration(protocol, final.name),
            metrics={"final_cases": float(len(final.cases))},
            verdict="preregistered",
        ),
        rows,
        artifacts=_frozen_copies(project_root),
    )


def verify_preregistration(
    project_root: Path, runs_dir: Path, run_id: str, protocol: Protocol
) -> str:
    """Refuse final execution unless the same run preregistered today's exact inputs."""
    directory = stage_directory(runs_dir, run_id, STAGE_PREREGISTRATION)
    if not directory.is_dir():
        raise FrozenInputError(f"final execution needs a preregistration bundle at {directory}")
    fingerprint = verify_run_bundle(directory)
    manifest = json.loads((directory / "manifest.json").read_text(encoding="ascii"))
    expected = input_fingerprints(project_root, protocol, "final")
    if manifest.get("input_fingerprints") != expected:
        raise FrozenInputError("final inputs differ from the preregistered fingerprints")
    return fingerprint


def publish_execution(
    project_root: Path,
    runs_dir: Path,
    run_id: str,
    stage: str,
    protocol: Protocol,
    execution: Execution,
    decision: Decision,
    compared: Sequence[Endpoint],
    extra: Mapping[str, object],
) -> PublishedBundle:
    """Publish one executed split with its ledger, report, and frozen-input copies."""
    inputs = input_fingerprints(project_root, protocol, execution.split.name)
    if isinstance(extra.get("preregistration"), str):
        inputs["preregistration_manifest"] = str(extra["preregistration"])
    artifacts: dict[str, str | bytes] = {
        "report.json": normalize_json(report_payload(protocol, execution, decision, compared))
    }
    artifacts.update(_frozen_copies(project_root))
    return publish_run_bundle(
        stage_directory(runs_dir, run_id, stage),
        BundleSpec(
            run_id=run_id,
            kind=f"{KIND}-{stage}",
            input_fingerprints=inputs,
            configuration={
                **_configuration(protocol, execution.split.name),
                **{key: value for key, value in extra.items() if key != "preregistration"},
                "engine_version": execution.engine_version,
                "filler_rows": execution.filler_rows,
                "repetitions": execution.repetitions,
            },
            metrics=manifest_metrics(protocol, execution),
            verdict=decision.verdict,
        ),
        case_rows(execution),
        artifacts=artifacts,
    )


def _configuration(protocol: Protocol, split: str) -> dict[str, object]:
    return {
        "baseline": protocol.baseline,
        "candidate": protocol.candidate,
        "confidence": protocol.confidence,
        "k_precision": protocol.k_precision,
        "k_quality": protocol.k_quality,
        "paradedb_version": protocol.paradedb_version,
        "primary_seed": protocol.primary_seed,
        "resamples": protocol.resamples,
        "sensitivity_seeds": list(protocol.sensitivity_seeds),
        "split": split,
    }


def _frozen_copies(project_root: Path) -> dict[str, str | bytes]:
    return {
        f"inputs/{name}": second_opinion_path(project_root, name).read_bytes()
        for name in ("arms.json", "protocol.json", "review.json")
    }

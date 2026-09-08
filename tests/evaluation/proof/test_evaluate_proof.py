from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main
from arxiv_int.evaluation.evaluate.errors import (
    ProofIntegrityError,
    ProofRedactionError,
    ProofUnknownCapabilityError,
)
from arxiv_int.evaluation.evaluate.paths import fixture_root, published_evaluation_dir
from arxiv_int.evaluation.evaluate.run import EvaluateRequest, run_evaluate
from arxiv_int.evaluation.evaluate.stage import EvaluateStage
from arxiv_int.evaluation.families import all_items, write_fixture_catalog
from arxiv_int.evaluation.fixtures.guard import item_ledger
from arxiv_int.evaluation.proof.checks import (
    current_fingerprints,
    redact_summary_text,
    refuse_corpus_leak,
    refuse_stale_fingerprints,
    validate_proof_manifest,
)
from arxiv_int.evaluation.proof.model import (
    ProofManifest,
    load_capability_registry,
    require_capability,
)
from arxiv_int.evaluation.proof.ops import (
    discover_proof_targets,
    publish_capability_proof,
    write_capability_registry,
    write_threshold_config,
)
from arxiv_int.interfaces.pipeline import StageContext, StageRunner
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.quality.project_root import discover_project_root


def test_evaluate_stage_publishes_a_replayable_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    from arxiv_int.runtime.project_root import find_project_root

    real_root = find_project_root()
    runs = tmp_path / "runs"
    first = run_evaluate(
        EvaluateRequest(
            run_id="eval-1",
            project_root=real_root,
            fixture_root=fixture_root(real_root),
            runs_dir=runs,
            seed=13,
        )
    )
    second = run_evaluate(
        EvaluateRequest(
            run_id="eval-2",
            project_root=real_root,
            fixture_root=fixture_root(real_root),
            runs_dir=runs,
            seed=13,
        )
    )
    assert first.ledger == second.ledger
    assert first.metrics == second.metrics
    assert first.verdict == second.verdict
    assert first.metrics["mean_positive"] > first.metrics["mean_negative"]
    assert published_evaluation_dir(runs, "eval-1").joinpath("manifest.json").is_file()
    stage = EvaluateStage()
    assert isinstance(stage, StageRunner)
    result = stage.run(
        StageContext(
            stage="evaluate",
            run_id="eval-stage",
            generation_id="eval-stage",
            silos=(SiloRoot("archive", tmp_path / "archive"),),
            results_dir=tmp_path / "stage-runs",
            options={
                "project_root": str(real_root),
                "fixture_root": str(fixture_root(real_root)),
                "runs_dir": str(tmp_path / "stage-runs"),
                "seed": "13",
            },
        )
    )
    assert result.outcome == "produced"


def test_proof_discovery_and_unknown_capability(tmp_path: Path) -> None:
    real_root = discover_project_root(Path(__file__))
    write_capability_registry(real_root)
    write_threshold_config(real_root)
    write_fixture_catalog(fixture_root(real_root))
    targets = discover_proof_targets(real_root)
    names = [item.capability_id for item in targets]
    assert "evaluation-foundation" in names
    assert "pipeline-control" in names
    assert "corpus-foundation" in names
    registry = load_capability_registry(real_root)
    with pytest.raises(ProofUnknownCapabilityError, match="unknown proof capability"):
        require_capability(registry, "not-a-capability")


def test_proof_publish_rejects_unvalidated_and_stale(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    real_root = discover_project_root(Path(__file__))
    write_capability_registry(real_root)
    write_fixture_catalog(fixture_root(real_root))
    published = publish_capability_proof(
        project_root=real_root,
        capability="evaluation-foundation",
        run_id="proof-1",
        results_dir=tmp_path / "results",
        runs_dir=tmp_path / "runs",
    )
    assert published.directory.joinpath("proof-manifest.json").is_file()
    assert "$" not in published.summary or "capability=" in published.summary
    with pytest.raises(ProofIntegrityError, match="unvalidated"):
        publish_capability_proof(
            project_root=real_root,
            capability="corpus-foundation",
            run_id="proof-2",
            results_dir=tmp_path / "results",
            runs_dir=tmp_path / "runs",
        )
    ledger = item_ledger(all_items())
    expected = current_fingerprints(real_root, ledger.fingerprint)
    stale = ProofManifest(
        schema_version=1,
        capability_id="evaluation-foundation",
        proof_id="stale",
        run_id="stale",
        data_class="raw",
        verdict="inconclusive",
        fingerprints={"code": "0" * 64, "fixtures": "1" * 64},
        stages={"evaluate": "validated"},
        validators={
            "evaluation-bundle": "pass",
            "identity-export": "pass",
            "item-ledger": "pass",
            "split-leakage": "pass",
            "stage:evaluate": "pass",
        },
        artifacts={"manifest.json": {"bytes": 1, "sha256": "a" * 64}},
    )
    with pytest.raises(Exception, match="stale"):
        refuse_stale_fingerprints(stale, expected)
    missing = dict(stale.as_json_dict())
    missing["artifacts"] = {}
    with pytest.raises(ProofIntegrityError, match="checksum"):
        validate_proof_manifest(
            missing, load_capability_registry(real_root)["evaluation-foundation"], expected
        )


def test_repository_summary_refuses_private_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RESULTS_DIR", "/mnt/results")
    assert redact_summary_text("wrote /mnt/results/proofs") == "wrote $RESULTS_DIR/proofs"
    with pytest.raises(ProofRedactionError, match="private path"):
        redact_summary_text("leaked /home/operator/archive")
    with pytest.raises(ProofRedactionError, match="unobfuscated person"):
        refuse_corpus_leak("summary mentioned Fixture Person Alpha")
    refuse_corpus_leak("capability=evaluation-foundation proof_id=0036")


def test_cli_evaluate_fixtures_and_proof(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    import logging

    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    real_root = discover_project_root(Path(__file__))
    parser = build_parser()
    assert parser.parse_args(["evaluation", "proof", "discover"]).proof_command == "discover"
    caplog.set_level(logging.INFO)
    assert main(["evaluation", "fixtures", "generate", "--project-root", str(real_root)]) == 0
    assert main(["evaluation", "fixtures", "check", "--project-root", str(real_root)]) == 0
    assert (
        main(
            [
                "evaluation",
                "evaluate",
                "--run-id",
                "cli-eval",
                "--runs-dir",
                str(tmp_path / "runs"),
                "--project-root",
                str(real_root),
            ]
        )
        == 0
    )
    assert (
        main(
            [
                "evaluation",
                "proof",
                "publish",
                "--capability",
                "missing-capability",
                "--run-id",
                "cli-proof",
                "--results-dir",
                str(tmp_path / "results"),
                "--runs-dir",
                str(tmp_path / "runs"),
                "--project-root",
                str(real_root),
            ]
        )
        == 1
    )

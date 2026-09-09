"""Cross-module evaluate, proof, and retired-path boundary checks."""

import json
from pathlib import Path

import pytest

from arxiv_int.cli import main
from arxiv_int.evaluation.bundles.errors import BundleExistsError
from arxiv_int.evaluation.evaluate.errors import (
    MissingEvidenceError,
    ProofExistsError,
    ProofRedactionError,
)
from arxiv_int.evaluation.evaluate.paths import (
    evaluation_artifact_dir,
    fixture_root,
    published_evaluation_dir,
    published_proof_dir,
)
from arxiv_int.evaluation.evaluate.run import EvaluateRequest, run_evaluate
from arxiv_int.evaluation.families import all_items
from arxiv_int.evaluation.fixtures.guard import item_ledger
from arxiv_int.evaluation.proof.ops import check_capability_proof, publish_capability_proof
from arxiv_int.resources.paths import configs_root


def test_evaluate_same_run_cannot_replace_the_bundle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    real_root = Path(__file__).resolve().parents[2]
    request = EvaluateRequest(
        run_id="eval-once",
        project_root=real_root,
        fixture_root=fixture_root(real_root),
        runs_dir=tmp_path / "runs",
        seed=13,
    )
    first = run_evaluate(request)
    with pytest.raises(BundleExistsError, match="already exists"):
        run_evaluate(request)
    bundle = published_evaluation_dir(tmp_path / "runs", "eval-once")
    assert json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    replay = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    assert first.bundle.fingerprint
    assert replay["verdict"] == first.verdict


def test_empty_resource_evidence_does_not_publish(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    real_root = Path(__file__).resolve().parents[2]
    with pytest.raises(MissingEvidenceError, match="latency"):
        run_evaluate(
            EvaluateRequest(
                run_id="eval-empty-resource",
                project_root=real_root,
                fixture_root=fixture_root(real_root),
                runs_dir=tmp_path / "runs",
                resource={"latencies_ms": []},
            )
        )
    assert not published_evaluation_dir(tmp_path / "runs", "eval-empty-resource").exists()


def test_proof_destination_cannot_be_replaced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    real_root = Path(__file__).resolve().parents[2]
    dest = published_proof_dir(tmp_path / "results", "evaluation-foundation", "proof-exist")
    dest.mkdir(parents=True)
    with pytest.raises(ProofExistsError, match="already exists"):
        publish_capability_proof(
            project_root=real_root,
            capability="evaluation-foundation",
            run_id="proof-exist",
            results_dir=tmp_path / "results",
            runs_dir=tmp_path / "runs",
        )


def test_leaking_or_identity_catalog_proof_tree_cannot_check(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    real_root = Path(__file__).resolve().parents[2]
    published = publish_capability_proof(
        project_root=real_root,
        capability="evaluation-foundation",
        run_id="proof-leak",
        results_dir=tmp_path / "results",
        runs_dir=tmp_path / "runs",
    )
    ledger = item_ledger(all_items())
    (published.directory / "note.txt").write_text("Fixture Person Alpha leaked\n", encoding="utf-8")
    with pytest.raises(ProofRedactionError, match="unobfuscated person"):
        check_capability_proof(published.directory, real_root, ledger.fingerprint)
    (published.directory / "note.txt").unlink()
    (published.directory / "identities.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ProofRedactionError, match=r"identities\.json"):
        check_capability_proof(published.directory, real_root, ledger.fingerprint)


def test_no_command_or_asset_can_export_proof_data_into_the_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    real_root = Path(__file__).resolve().parents[2]
    for argv in (
        ["evaluation", "export-proof", "--source-bundle", str(tmp_path), "--run-id", "x"],
        ["evaluation", "identity-policy", "check"],
    ):
        with pytest.raises(SystemExit):
            main(argv)
    assert not (configs_root(real_root) / "evaluation" / "proof-identity-policy.json").exists()
    published = publish_capability_proof(
        project_root=real_root,
        capability="evaluation-foundation",
        run_id="proof-no-export",
        results_dir=tmp_path / "results",
        runs_dir=tmp_path / "runs",
    )
    assert sorted(item.name for item in published.directory.iterdir()) == [
        "fingerprint.json",
        "proof-manifest.json",
        "summary.txt",
    ]
    fingerprint = json.loads((published.directory / "fingerprint.json").read_text(encoding="utf-8"))
    assert fingerprint == {"data_class": "raw", "raw_fingerprint": published.fingerprint}
    manifest = json.loads((published.directory / "proof-manifest.json").read_text(encoding="utf-8"))
    assert manifest["verdict"] and manifest["artifacts"]
    assert "identity-export" not in manifest["validators"]
    ledger = item_ledger(all_items())
    assert check_capability_proof(published.directory, real_root, ledger.fingerprint)


def test_retired_proof_archive_is_not_an_evaluation_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROOF_ARCHIVE_DIR", str(tmp_path / "legacy-proof"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    path = evaluation_artifact_dir(tmp_path / "proj", "run-1")
    assert path == tmp_path / "data" / "evaluation" / "run-1"
    assert "legacy-proof" not in str(path)

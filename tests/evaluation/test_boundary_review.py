"""Cross-module evaluate, proof, export, and retired-archive boundary checks."""

import json
from pathlib import Path

import pytest

from arxiv_int.evaluation.bundles import publish_run_bundle
from arxiv_int.evaluation.bundles.errors import BundleExistsError
from arxiv_int.evaluation.bundles.manifest import canonical_json
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
from arxiv_int.evaluation.export.exporter import ExportMapping, ExportRequest, export_proof_bundle
from arxiv_int.evaluation.families import all_items
from arxiv_int.evaluation.fixtures.guard import item_ledger
from arxiv_int.evaluation.proof.ops import check_capability_proof, publish_capability_proof
from arxiv_int.evaluation.scoring.geo import score_geotemporal, score_ontology
from tests.evaluation.bundles.bundle_support import spec


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


def test_exported_ontology_and_geotemporal_meanings_survive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    items = {item.item_id: item for item in all_items()}
    ontology = items["ontology-draft-tuning"]
    geo = items["geo-unknown-crs-final"]
    payload = {
        "draft_allowed": ontology.gold["allowed"],
        "action": ontology.gold["action"],
        "source_valid_start": geo.gold["source_valid_start"],
        "recorded_time": geo.gold["recorded_time"],
        "unknown_crs": geo.gold["unknown_crs"],
        "crs": geo.gold["crs"],
        "label": "Fixture Person Alpha",
    }
    source = tmp_path / "bundle"
    publish_run_bundle(
        source,
        spec(),
        [{"item_id": ontology.item_id, "score": 1.0}],
        artifacts={
            "items.json": canonical_json(payload).decode("utf-8"),
            "identities.json": canonical_json(
                {
                    "schema_version": 1,
                    "entities": [
                        {
                            "id": "person:alpha",
                            "kind": "person",
                            "labels": ["Fixture Person Alpha"],
                            "aliases": [],
                        }
                    ],
                    "fields": [],
                    "spans": [],
                }
            ).decode("utf-8"),
        },
    )
    dest = tmp_path / "export"
    export_proof_bundle(
        ExportRequest(
            source_bundle=source,
            mappings=(
                ExportMapping("items.json", Path("items.json")),
                ExportMapping("manifest.json", Path("manifest.json")),
            ),
            run_id="boundary-export",
            project_root=tmp_path / "proj",
            destination_root=dest,
        )
    )
    rewritten = json.loads((dest / "items.json").read_text(encoding="utf-8"))
    assert "Fixture Person Alpha" not in json.dumps(rewritten)
    assert rewritten["draft_allowed"] is False
    assert rewritten["unknown_crs"] is True
    assert rewritten["crs"] in {None, ""}
    assert score_ontology(ontology.gold, ontology.gold)["draft_refused"] == 1.0
    assert score_geotemporal(rewritten, rewritten)["source_recorded_distinct"] == 1.0
    assert score_geotemporal(rewritten, rewritten)["unknown_crs_kept"] == 1.0


def test_retired_proof_archive_is_not_an_evaluation_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("PROOF_ARCHIVE_DIR", str(tmp_path / "legacy-proof"))
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    path = evaluation_artifact_dir(tmp_path / "proj", "run-1")
    assert path == tmp_path / "data" / "evaluation" / "run-1"
    assert "legacy-proof" not in str(path)

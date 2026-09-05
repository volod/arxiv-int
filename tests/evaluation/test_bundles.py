import json
from pathlib import Path

import pytest

from arxiv_int.evaluation.bundles import BundleSpec, publish_run_bundle, verify_run_bundle


def _spec() -> BundleSpec:
    return BundleSpec(
        run_id="run-1",
        kind="retrieval",
        input_fingerprints={"gold": "sha256:abc"},
        configuration={"k": 5},
        metrics={"recall_at_k": 1.0},
        verdict="adopt",
    )


def test_bundle_is_published_with_checksums_and_no_staging_residue(tmp_path: Path) -> None:
    target = tmp_path / "run-1"

    published = publish_run_bundle(
        target,
        _spec(),
        [{"item_id": "b", "score": 1.0}, {"item_id": "a", "score": 0.0}],
        artifacts={"reports/summary.txt": "ok\n"},
    )

    assert published.manifest == target / "manifest.json"
    assert len(published.fingerprint) == 64
    assert verify_run_bundle(target) is True
    manifest = json.loads(published.manifest.read_text(encoding="utf-8"))
    assert set(manifest["artifacts"]) == {"reports/summary.txt", "scores.jsonl"}
    score_lines = (target / "scores.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["item_id"] for line in score_lines] == ["b", "a"]
    assert not list(tmp_path.glob(".run-1.tmp-*"))


def test_bundle_never_overwrites_published_evidence(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, _spec(), [])

    with pytest.raises(FileExistsError, match="already exists"):
        publish_run_bundle(target, _spec(), [{"changed": True}])


def test_bundle_verification_detects_corruption_and_unregistered_files(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, _spec(), [{"score": 1.0}])
    (target / "scores.jsonl").write_text("changed\n", encoding="utf-8")

    with pytest.raises(ValueError, match="failed verification"):
        verify_run_bundle(target)

    (target / "scores.jsonl").unlink()
    (target / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="do not match manifest"):
        verify_run_bundle(target)


def test_bundle_rejects_artifact_path_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="invalid bundle artifact"):
        publish_run_bundle(tmp_path / "run-1", _spec(), [], artifacts={"../escape": "bad"})

    assert not (tmp_path / "run-1").exists()
    assert not list(tmp_path.glob(".run-1.tmp-*"))

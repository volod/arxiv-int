import json
from pathlib import Path

import pytest

from arxiv_int.evaluation.bundle_errors import BundleExistsError, BundleIntegrityError
from arxiv_int.evaluation.bundle_layout import HASH_CHUNK_BYTES
from arxiv_int.evaluation.bundles import publish_run_bundle, verify_run_bundle
from tests.evaluation.bundle_support import spec


def test_bundle_is_published_with_checksums_and_no_staging_residue(tmp_path: Path) -> None:
    target = tmp_path / "run-1"

    published = publish_run_bundle(
        target,
        spec(),
        [{"item_id": "b", "score": 1.0}, {"item_id": "a", "score": 0.0}],
        artifacts={"reports/summary.txt": "ok\n"},
    )

    assert published.manifest == target / "manifest.json"
    assert len(published.fingerprint) == 64
    assert verify_run_bundle(target) == published.fingerprint
    manifest = json.loads(published.manifest.read_text(encoding="utf-8"))
    assert set(manifest["artifacts"]) == {"reports/summary.txt", "scores.jsonl"}
    score_lines = (target / "scores.jsonl").read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["item_id"] for line in score_lines] == ["b", "a"]
    assert not list(tmp_path.glob(".run-1.tmp-*"))


def test_valid_bundle_replays_with_a_stable_fingerprint(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    published = publish_run_bundle(target, spec(), [{"score": 1.0}])

    assert verify_run_bundle(target) == published.fingerprint
    assert verify_run_bundle(target) == published.fingerprint


def test_bundle_never_overwrites_published_evidence(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [])
    original = (target / "scores.jsonl").read_bytes()

    with pytest.raises(BundleExistsError, match="already exists"):
        publish_run_bundle(target, spec(), [{"changed": True}])

    assert (target / "scores.jsonl").read_bytes() == original
    assert verify_run_bundle(target)


def test_bundle_verification_detects_corruption_and_unregistered_files(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [{"score": 1.0}])
    (target / "scores.jsonl").write_text("changed\n", encoding="utf-8")

    with pytest.raises(BundleIntegrityError, match="failed verification"):
        verify_run_bundle(target)

    (target / "scores.jsonl").unlink()
    (target / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(BundleIntegrityError, match="do not match manifest"):
        verify_run_bundle(target)


def test_chunked_artifact_digest_matches_the_full_payload(tmp_path: Path) -> None:
    payload = b"a" * (HASH_CHUNK_BYTES + 17)
    target = tmp_path / "run-1"
    published = publish_run_bundle(target, spec(), [], artifacts={"blob.bin": payload})

    assert verify_run_bundle(target) == published.fingerprint
    digest = json.loads(published.manifest.read_text(encoding="utf-8"))["artifacts"]["blob.bin"]
    assert digest["bytes"] == len(payload)

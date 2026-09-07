import os
from pathlib import Path

import pytest

from arxiv_int.evaluation.bundle_errors import BundleExistsError, BundleLayoutError
from arxiv_int.evaluation.bundles import publish_run_bundle, verify_run_bundle
from tests.evaluation.bundle_support import spec


def test_bundle_rejects_artifact_path_escape(tmp_path: Path) -> None:
    with pytest.raises(BundleLayoutError, match="invalid bundle artifact"):
        publish_run_bundle(tmp_path / "run-1", spec(), [], artifacts={"../escape": "bad"})

    assert not (tmp_path / "run-1").exists()
    assert not list(tmp_path.glob(".run-1.tmp-*"))


def test_verification_rejects_an_external_symlink_with_matching_bytes(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [{"score": 1.0}])
    original = (target / "scores.jsonl").read_bytes()
    outside = tmp_path / "outside"
    outside.mkdir()
    twin = outside / "scores.jsonl"
    twin.write_bytes(original)
    (target / "scores.jsonl").unlink()
    (target / "scores.jsonl").symlink_to(twin)

    with pytest.raises(BundleLayoutError, match="not a regular file"):
        verify_run_bundle(target)


def test_verification_rejects_a_symlinked_artifact_directory(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [], artifacts={"reports/summary.txt": "ok\n"})
    original = (target / "reports" / "summary.txt").read_bytes()
    outside = tmp_path / "outside" / "reports"
    outside.mkdir(parents=True)
    (outside / "summary.txt").write_bytes(original)
    (target / "reports" / "summary.txt").unlink()
    (target / "reports").rmdir()
    (target / "reports").symlink_to(outside)

    with pytest.raises(BundleLayoutError, match="not a regular directory"):
        verify_run_bundle(target)


def test_verification_rejects_a_fifo_in_place_of_an_artifact(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [{"score": 1.0}])
    payload = (target / "scores.jsonl").read_bytes()
    (target / "scores.jsonl").unlink()
    os.mkfifo(target / "scores.jsonl")
    try:
        with pytest.raises(BundleLayoutError, match="not a regular file"):
            verify_run_bundle(target)
    finally:
        (target / "scores.jsonl").unlink()
        (target / "scores.jsonl").write_bytes(payload)


def test_verification_rejects_a_symlinked_manifest(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [])
    real = (target / "manifest.json").read_bytes()
    outside = tmp_path / "outside.json"
    outside.write_bytes(real)
    (target / "manifest.json").unlink()
    (target / "manifest.json").symlink_to(outside)

    with pytest.raises(BundleLayoutError, match="not a regular file"):
        verify_run_bundle(target)


def test_publication_refuses_a_destination_symlink(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    target.symlink_to(elsewhere)

    with pytest.raises(BundleExistsError, match="already exists"):
        publish_run_bundle(target, spec(), [{"score": 1.0}])

    assert target.is_symlink()
    assert list(elsewhere.iterdir()) == []


def test_publication_refuses_reserved_artifact_names(tmp_path: Path) -> None:
    with pytest.raises(BundleLayoutError, match="reserved"):
        publish_run_bundle(tmp_path / "run-1", spec(), [], artifacts={"manifest.json": "nope"})
    with pytest.raises(BundleLayoutError, match="reserved"):
        publish_run_bundle(tmp_path / "run-2", spec(), [], artifacts={"scores.jsonl": "nope"})
    assert not (tmp_path / "run-1").exists()
    assert not (tmp_path / "run-2").exists()

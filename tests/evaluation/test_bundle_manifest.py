import json
from pathlib import Path

import pytest

from arxiv_int.evaluation.bundle_errors import BundleManifestError
from arxiv_int.evaluation.bundles import BundleSpec, publish_run_bundle, verify_run_bundle
from tests.evaluation.bundle_support import spec


def test_bundle_spec_rejects_missing_identities() -> None:
    with pytest.raises(BundleManifestError, match="run_id"):
        BundleSpec(
            run_id="",
            kind="retrieval",
            input_fingerprints={"gold": "sha256:abc"},
            configuration={},
            metrics={},
            verdict="adopt",
        )
    with pytest.raises(BundleManifestError, match="kind"):
        BundleSpec(
            run_id="run-1",
            kind=" kind",
            input_fingerprints={"gold": "sha256:abc"},
            configuration={},
            metrics={},
            verdict="adopt",
        )


def test_verification_rejects_a_corrupt_manifest(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [{"score": 1.0}])
    (target / "manifest.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(BundleManifestError, match="not valid JSON"):
        verify_run_bundle(target)


def test_verification_rejects_missing_manifest_identities(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [{"score": 1.0}])
    payload = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    del payload["run_id"]
    (target / "manifest.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    with pytest.raises(BundleManifestError, match="missing or malformed"):
        verify_run_bundle(target)


def test_verification_rejects_a_noncanonical_manifest(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [{"score": 1.0}])
    payload = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    (target / "manifest.json").write_text(json.dumps(payload, indent=4) + "\n", encoding="utf-8")

    with pytest.raises(BundleManifestError, match="not canonical"):
        verify_run_bundle(target)


def test_verification_rejects_an_invalid_artifact_digest(tmp_path: Path) -> None:
    target = tmp_path / "run-1"
    publish_run_bundle(target, spec(), [{"score": 1.0}])
    payload = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    payload["artifacts"]["scores.jsonl"]["sha256"] = "not-a-digest"
    (target / "manifest.json").write_bytes(
        (json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n").encode()
    )

    with pytest.raises(BundleManifestError, match="invalid artifact record"):
        verify_run_bundle(target)

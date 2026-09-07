"""Evidence must cover the selected generation and all attached data tests."""

import json
from pathlib import Path

import pytest

from arxiv_int.transformations.validation import ValidationEvidenceError, validated_relations


def _artifacts(path: Path) -> tuple[dict, dict]:
    manifests = path / "manifests"
    manifests.mkdir()
    manifest = {
        "metadata": {"invocation_id": "current"},
        "nodes": {
            "model.docs": {
                "name": "docs",
                "alias": "docs__g_v1",
                "schema": "derived",
                "resource_type": "model",
            },
            "test.key": {"resource_type": "test", "depends_on": {"nodes": ["model.docs"]}},
            "test.null": {"resource_type": "test", "depends_on": {"nodes": ["model.docs"]}},
        },
    }
    results = {
        "metadata": {"invocation_id": "current"},
        "results": [
            {"unique_id": "model.docs", "status": "success"},
            {"unique_id": "test.key", "status": "pass"},
            {"unique_id": "test.null", "status": "pass"},
        ],
    }
    return manifest, results


def _write(path: Path, manifest: dict, results: dict) -> None:
    (path / "manifests/manifest.json").write_text(json.dumps(manifest))
    (path / "manifests/run_results.json").write_text(json.dumps(results))


@pytest.mark.parametrize("command", ["build", "test"])
def test_complete_evidence_resolves_actual_selected_relations(tmp_path: Path, command: str) -> None:
    manifest, results = _artifacts(tmp_path)
    if command == "test":
        results["results"] = results["results"][1:]
    _write(tmp_path, manifest, results)
    assert validated_relations(tmp_path, "v1", command) == ("derived.docs__g_v1",)


@pytest.mark.parametrize(
    "case",
    ["stale", "missing-test", "failed-test", "wrong-generation", "canonical-schema", "no-models"],
)
def test_incomplete_or_wrong_generation_evidence_refuses(tmp_path: Path, case: str) -> None:
    manifest, results = _artifacts(tmp_path)
    if case == "stale":
        results["metadata"]["invocation_id"] = "old"
    elif case == "missing-test":
        results["results"].pop()
    elif case == "failed-test":
        results["results"][-1]["status"] = "fail"
    elif case == "wrong-generation":
        manifest["nodes"]["model.docs"]["alias"] = "docs__g_active"
    elif case == "canonical-schema":
        manifest["nodes"]["model.docs"]["schema"] = "corpus"
    else:
        results["results"] = []
    _write(tmp_path, manifest, results)
    with pytest.raises(ValidationEvidenceError):
        validated_relations(tmp_path, "v1", "build")

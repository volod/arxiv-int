"""Actionable refusal of stale immutable classification scheme snapshots."""

import json
from pathlib import Path

import pytest

from arxiv_int.classification.stage import _scheme_snapshot
from tests.classification.stage_helpers import classify_context
from tests.pipeline.chain import run_chain


def test_stale_scheme_names_fingerprint_and_fresh_run_recovery(tmp_path: Path) -> None:
    run = run_chain(tmp_path, fixtures={"source.txt": "Machine learning data science"})
    context = classify_context(run)
    _scheme_snapshot(context, tmp_path)
    manifest = context.results_dir / "runs" / context.run_id / "classification/scheme/manifest.json"
    payload = json.loads(manifest.read_text(encoding="ascii"))
    payload["builderVersion"] = "obsolete-builder"
    manifest.write_text(json.dumps(payload, ensure_ascii=True), encoding="ascii")

    with pytest.raises(ValueError) as error:
        _scheme_snapshot(context, tmp_path)

    message = str(error.value)
    assert "builder fingerprint" in message
    assert "make run-create" in message
    assert "make classification-scheme RUN_ID=<new-run-id>" in message
    assert json.loads(manifest.read_text(encoding="ascii")) == payload

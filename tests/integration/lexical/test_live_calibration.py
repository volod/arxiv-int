"""Declared live calibration of Russian tokenizer and query profiles."""

import json
import os
import shutil
from pathlib import Path

import pytest

from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.retrieval.calibration import run_calibration
from arxiv_int.stores.postgres.apply import apply_revisions
from arxiv_int.stores.postgres.disposable import disposable_store, image_present
from arxiv_int.stores.postgres_image.pins import load_image_pins

pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_LEXICAL_CALIBRATION") != "1",
        reason="set ARXIV_INT_RUN_LEXICAL_CALIBRATION=1 for the declared calibration run",
    ),
]


def _root() -> Path:
    return discover_project_root(Path(__file__))


def test_live_russian_profile_calibration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _root()
    pins = load_image_pins(root)
    if not image_present(pins.local_image_ref):
        pytest.skip(f"image {pins.local_image_ref} is not present; build it first")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="cal-schema", revision="head").ok
        outcome = run_calibration(
            project_root=root,
            database_url=store.url,
            runs_dir=tmp_path / "runs",
            run_id="cal-live",
        )
    assert outcome.verdict == "adopt"
    assert outcome.selected_profile == "unicode-russian-safe-v1"
    assert outcome.reindex_required is False
    assert len(outcome.manifest_fingerprint) == 64
    assert outcome.engine_version == "0.25.6"
    manifest = json.loads((outcome.bundle_dir / "manifest.json").read_text(encoding="ascii"))
    assert manifest["configuration"]["final_items"] == 12
    comparison = next(item for item in outcome.comparisons if item.name == "query-normalization")
    assert comparison.paired.wins >= 6
    assert comparison.paired.losses == 0

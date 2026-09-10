"""Declared live check of the lexical second-opinion harness on the pinned engine."""

import json
import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from arxiv_int.evaluation.bundles import verify_run_bundle
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.retrieval.second_opinion import Overrides, run_stage
from arxiv_int.retrieval.second_opinion.protocol import load_protocol
from arxiv_int.retrieval.second_opinion.splits import FrozenInputError
from arxiv_int.stores.postgres.apply import apply_revisions
from arxiv_int.stores.postgres.disposable import disposable_store, image_present
from arxiv_int.stores.postgres_image.pins import load_image_pins

pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_LEXICAL_SECOND_OPINION") != "1",
        reason="set ARXIV_INT_RUN_LEXICAL_SECOND_OPINION=1 for the declared live harness run",
    ),
]
SMALL = Overrides(filler_chunks=400, build_repetitions=2, query_repetitions=2)


def test_live_second_opinion_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = discover_project_root(Path(__file__))
    pins = load_image_pins(root)
    if not image_present(pins.local_image_ref):
        pytest.skip(f"image {pins.local_image_ref} is not present; build it first")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    runs = tmp_path / "runs"
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="so-schema", revision="head").ok
        with pytest.raises(FrozenInputError, match="preregistration"):
            run_stage(
                project_root=root,
                database_url=store.url,
                runs_dir=runs,
                run_id="so-live",
                stage="final",
            )
        with pytest.raises(ValueError, match="only the development stage"):
            run_stage(
                project_root=root, database_url=store.url, runs_dir=runs, run_id="so-live",
                stage="final", overrides=SMALL,
            )  # fmt: skip
        outcome = run_stage(
            project_root=root, database_url=store.url, runs_dir=runs, run_id="so-live",
            stage="development", overrides=SMALL,
        )  # fmt: skip
        engine = create_engine(store.url)
        with engine.connect() as connection:
            leftovers = connection.execute(
                text("SELECT count(*) FROM pg_tables WHERE tablename LIKE 'so\\_%'")
            ).scalar()
        engine.dispose()
    assert leftovers == 0
    assert outcome.engine_version == load_protocol(root).paradedb_version
    assert verify_run_bundle(outcome.bundle_dir) == outcome.manifest_fingerprint
    report = json.loads((outcome.bundle_dir / "report.json").read_text(encoding="ascii"))
    protocol = load_protocol(root)
    assert {item["arm"] for item in report["arms"]} == {arm.arm_id for arm in protocol.arms}
    assert all(len(build["build_seconds"]) == 2 for build in report["builds"])
    assert report["execution"]["filler_rows"] == 400
    assert outcome.verdict in {"adopt", "retain baseline", "inconclusive"}
    rows = (outcome.bundle_dir / "scores.jsonl").read_text(encoding="ascii").splitlines()
    assert len(rows) == len(protocol.arms) * 122

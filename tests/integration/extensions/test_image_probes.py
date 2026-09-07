"""Live disposable probes for the project-owned PostgreSQL image."""

import os
import shutil
from pathlib import Path

import pytest

from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres_image.build import build_postgres_image
from arxiv_int.stores.postgres_image.pins import load_image_pins
from arxiv_int.stores.postgres_image.probes import run_extension_probes

pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_EXTENSION_PROBES") != "1",
        reason="set ARXIV_INT_RUN_EXTENSION_PROBES=1 for the declared disposable image run",
    ),
]


def test_extension_probes_pass_on_disposable_pgdata(tmp_path: Path) -> None:
    root = discover_project_root(Path(__file__))
    pins = load_image_pins(root)
    build_postgres_image(root, pins=pins, no_cache=False)
    report = run_extension_probes(root, tmp_path / "pgdata", pins=pins)
    assert report.all_core_passed, report.summary
    assert report.age_compatible, report.summary
    assert report.summary["cypher"] == "pass"
    assert report.summary["bm25_vector"] == "pass"
    assert report.summary["dump_restore"] == "pass"
    assert report.summary["restart"] == "pass"

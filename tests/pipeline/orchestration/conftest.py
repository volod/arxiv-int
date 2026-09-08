"""Shared fixture-run helpers for DAG orchestration tests."""

from pathlib import Path

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.context import (
    RunContext,
    allocate_run_id,
    config_fingerprint,
    snapshot_silos,
)
from arxiv_int.pipeline.persist import save_context


def make_context(tmp_path: Path, *, profile: str = "fixture", text: str = "one") -> RunContext:
    """Build a frozen fixture run with one archive silo."""
    archive = tmp_path / "archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "doc.txt").write_text(text, encoding="utf-8")
    results = tmp_path / "results"
    results.mkdir(parents=True, exist_ok=True)
    runs = tmp_path / "runs"
    root = tmp_path / "project"
    root.mkdir(parents=True, exist_ok=True)
    silos = (SiloRoot("default", archive),)
    secret = {"ARCHIVE_DIR": str(archive), "RESULTS_DIR": str(results)}
    run_id = allocate_run_id()
    context = RunContext(
        run_id,
        run_id,
        profile,
        config_fingerprint(profile, secret),
        snapshot_silos(silos),
        silos,
        results,
        runs,
        root,
        secret,
        {},
    )
    save_context(context)
    return context

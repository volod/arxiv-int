"""Shared helpers for integrated classification-stage tests."""

import json
from dataclasses import replace
from pathlib import Path

import pytest

from arxiv_int.classification.stage import ClassificationStage
from arxiv_int.pipeline.control.artifacts import hash_file
from tests.pipeline.chain import ChainRun


def classify(run: ChainRun):
    """Run classify against the chain's sealed inventory and normalization outputs."""
    inventory = run.manifest(run.inventory)
    normalization = run.manifest(run.normalize)
    options = {
        **dict(run.context.options),
        "runs_dir": str(run.context.results_dir / "runs"),
        "inventory_manifest": str(inventory),
        "inventory_manifest_sha256": hash_file(inventory)[0],
        "normalization_manifest": str(normalization),
        "normalization_manifest_sha256": hash_file(normalization)[0],
    }
    context = replace(run.context, stage="classify", options=options)
    return ClassificationStage().run(context)


def rows(manifest: Path) -> list[dict[str, object]]:
    """Read all file-classification rows from one sealed manifest."""
    summary = json.loads(manifest.read_text(encoding="ascii"))
    root = Path(str(summary["roots"]["file-classifications"]))
    polars = pytest.importorskip("polars")
    return polars.read_parquet(sorted(root.glob("part-*.parquet"))).to_dicts()

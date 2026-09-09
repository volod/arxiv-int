"""Synthetic silos and real production inventory stage contexts."""

import json
from pathlib import Path

import pytest

from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.inventory.stage import InventoryStage


@pytest.fixture
def context(tmp_path: Path) -> StageContext:
    sources = tmp_path / "sources"
    sources.mkdir()
    return StageContext(
        "inventory",
        "run-fixture",
        "run-fixture",
        (SiloRoot("one", sources),),
        tmp_path / "results",
        {"project_root": str(Path.cwd())},
    )


def run_inventory(context: StageContext) -> tuple[dict, list[dict], Path]:
    result = InventoryStage().run(context)
    manifest = Path(result.outputs[0].partition["manifest"])
    summary = json.loads(manifest.read_text())
    rows = []
    for path in sorted(manifest.parent.glob("*.metadata.jsonl")):
        rows.extend(json.loads(line) for line in path.read_text().splitlines())
    return summary, rows, manifest

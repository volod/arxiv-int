"""Registered preflight worker readability and path-free artifacts."""

from pathlib import Path

import pytest

from arxiv_int.interfaces.pipeline import StageContext, StageRunner
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.publish.preflight import PreflightStage, preflight_run
from arxiv_int.pipeline.run.errors import PreflightRefusedError
from tests.pipeline.conftest import make_context


def test_preflight_stage_is_a_runner_and_refuses_unreadable(tmp_path: Path) -> None:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "doc.txt").write_text("ok", encoding="ascii")
    stage = PreflightStage()
    assert isinstance(stage, StageRunner)
    result = stage.run(
        StageContext(
            "preflight",
            "run-preflight",
            "run-preflight",
            (SiloRoot("default", archive),),
            tmp_path / "results",
            {"document_id": "shard-a"},
        )
    )
    assert result.outcome == "produced"
    assert "archive silos readable" in result.detail
    assert "/home/" not in result.detail
    assert result.outputs[0].partition["shard"] == "shard-a"
    context = make_context(tmp_path)
    missing = tmp_path / "gone"
    from dataclasses import replace

    broken = replace(context, silos=(replace(context.silos[0], root=missing),))
    with pytest.raises(PreflightRefusedError, match="not readable"):
        preflight_run(broken)

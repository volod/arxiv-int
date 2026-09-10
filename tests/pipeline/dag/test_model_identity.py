"""Model file changes invalidate extraction even with unchanged tool versions."""

from dataclasses import replace
from pathlib import Path

from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.dag.execute import stage_identity
from arxiv_int.pipeline.dag.registry import ResourceEstimate, StageSpec
from arxiv_int.pipeline.run.context import RunContext


def test_model_bytes_invalidate_extract_only(tmp_path: Path) -> None:
    cache = tmp_path / "models"
    assets = cache / "docling"
    assets.mkdir(parents=True)
    weights = assets / "weights.bin"
    weights.write_bytes(b"model-a")
    context = RunContext(
        "run-test",
        "run-test",
        "fixture",
        "config",
        "source",
        (SiloRoot("primary", tmp_path / "archive"),),
        tmp_path / "results",
        tmp_path / "runs",
        tmp_path,
        {"MODEL_CACHE_DIR": str(cache)},
        {},
    )
    extract = StageSpec("extract", "1", (), (), (), ResourceEstimate(), (), (), None)
    inventory = replace(extract, name="inventory")
    before = stage_identity(extract, context, ())
    unrelated = stage_identity(inventory, context, ())
    weights.write_bytes(b"model-b")
    assert stage_identity(extract, context, ()) != before
    assert stage_identity(inventory, context, ()) == unrelated
    weights.unlink()
    assert stage_identity(extract, context, ()) != before

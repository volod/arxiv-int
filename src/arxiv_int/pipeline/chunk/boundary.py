"""Executed producer-boundary checks for source-aligned chunking."""

from arxiv_int.pipeline.control.quality import QualityCheck
from arxiv_int.pipeline.quality.bound import ProductionQuality
from arxiv_int.pipeline.run.context import RunContext


class ChunkQuality(ProductionQuality):
    """Permit publication after chunk contract and source-alignment checks pass."""

    def __init__(self, context: RunContext) -> None:
        from arxiv_int.pipeline.chunk.stage import chunk_root
        from arxiv_int.pipeline.dag.execute import stage_context

        chunk_root(stage_context(context, "chunk"))

    def checks(self) -> tuple[QualityCheck, ...]:
        return (QualityCheck("chunking.contracts-and-source-spans", "pass", "global", "error"),)

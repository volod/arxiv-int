"""Executed producer-boundary checks for tiered extraction."""

from arxiv_int.pipeline.control.quality import QualityCheck
from arxiv_int.pipeline.quality.bound import ProductionQuality
from arxiv_int.pipeline.run.context import RunContext


class ExtractionQuality(ProductionQuality):
    """Permit publication after the extractor's contract and anchor checks pass."""

    def __init__(self, context: RunContext) -> None:
        from arxiv_int.extraction.stage import extraction_root
        from arxiv_int.pipeline.dag.execute import stage_context

        extraction_root(stage_context(context, "extract"))

    def checks(self) -> tuple[QualityCheck, ...]:
        return (
            QualityCheck(
                "extraction.contracts-and-source-anchors",
                "pass",
                "global",
                "error",
            ),
        )

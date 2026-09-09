"""Executed source-scope preconditions for the shipped source-set stages."""

from arxiv_int.pipeline.control.quality import QualityCheck
from arxiv_int.pipeline.inventory.stage import inventory_root
from arxiv_int.pipeline.quality.bound import ProductionQuality
from arxiv_int.pipeline.run.context import RunContext


class SourceSetQuality(ProductionQuality):
    """Preconditions permit work; the inventory producer supplies completed data checks."""

    def __init__(self, context: RunContext, stage: str) -> None:
        from arxiv_int.pipeline.dag.execute import stage_context

        inventory_root(stage_context(context, stage))

    def checks(self) -> tuple[QualityCheck, ...]:
        return (QualityCheck("source-set.declarations-and-containment", "pass", "global", "error"),)

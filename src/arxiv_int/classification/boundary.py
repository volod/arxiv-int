"""Executed producer-boundary checks for hierarchical file classification."""

from arxiv_int.pipeline.control.quality import QualityCheck
from arxiv_int.pipeline.quality.bound import ProductionQuality
from arxiv_int.pipeline.run.context import RunContext


class ClassificationQuality(ProductionQuality):
    """Permit publication after mapping contracts and exact accounting pass."""

    def __init__(self, context: RunContext) -> None:
        from arxiv_int.classification.stage import classification_root
        from arxiv_int.pipeline.dag.execute import stage_context

        classification_root(stage_context(context, "classify"))

    def checks(self) -> tuple[QualityCheck, ...]:
        return (QualityCheck("classification.contracts-and-accounting", "pass", "global", "error"),)

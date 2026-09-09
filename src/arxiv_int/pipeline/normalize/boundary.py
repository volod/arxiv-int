"""Executed producer-boundary checks for text normalization."""

from arxiv_int.pipeline.control.quality import QualityCheck
from arxiv_int.pipeline.quality.bound import ProductionQuality
from arxiv_int.pipeline.run.context import RunContext


class NormalizeQuality(ProductionQuality):
    """Permit publication after normalization contract and offset checks pass."""

    def __init__(self, context: RunContext) -> None:
        from arxiv_int.pipeline.dag.execute import stage_context
        from arxiv_int.pipeline.normalize.stage import normalization_root

        normalization_root(stage_context(context, "normalize"))

    def checks(self) -> tuple[QualityCheck, ...]:
        return (QualityCheck("normalization.contracts-and-offset-maps", "pass", "global", "error"),)

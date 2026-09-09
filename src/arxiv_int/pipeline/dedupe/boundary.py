"""Executed producer-boundary checks for duplicate grouping."""

from arxiv_int.pipeline.control.quality import QualityCheck
from arxiv_int.pipeline.quality.bound import ProductionQuality
from arxiv_int.pipeline.run.context import RunContext


class DedupeQuality(ProductionQuality):
    """Permit publication after grouping contract and reversibility checks pass."""

    def __init__(self, context: RunContext) -> None:
        from arxiv_int.pipeline.dag.execute import stage_context
        from arxiv_int.pipeline.dedupe.stage import dedupe_root

        dedupe_root(stage_context(context, "dedupe"))

    def checks(self) -> tuple[QualityCheck, ...]:
        return (QualityCheck("dedupe.contracts-and-reversible-groups", "pass", "global", "error"),)

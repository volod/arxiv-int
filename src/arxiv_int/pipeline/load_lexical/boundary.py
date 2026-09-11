"""Executed producer-boundary checks for the lexical load and index build."""

from arxiv_int.pipeline.control.quality import QualityCheck
from arxiv_int.pipeline.quality.bound import ProductionQuality
from arxiv_int.pipeline.run.context import RunContext


class LoadLexicalQuality(ProductionQuality):
    """Permit publication after load reconciliation and index activation pass."""

    def __init__(self, context: RunContext) -> None:
        from arxiv_int.pipeline.dag.execute import stage_context
        from arxiv_int.pipeline.load_lexical.stage import lexical_root

        lexical_root(stage_context(context, "load-lexical"))

    def checks(self) -> tuple[QualityCheck, ...]:
        return (QualityCheck("lexical.load-reconciliation-and-index", "pass", "global", "error"),)

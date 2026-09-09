"""Contract-derived document/span validation for bounded extraction batches."""

from pathlib import Path

from arxiv_int.pipeline.lake.validate import ContractBatchValidator, SnapshotValidator

__all__ = ["ContractBatchValidator", "ExtractionValidator"]


class ExtractionValidator(SnapshotValidator):
    """Document and span validators with one combined quality identity."""

    def __init__(self, project_root: Path) -> None:
        super().__init__(project_root, ("documents", "spans"))
        self.documents = self["documents"]
        self.spans = self["spans"]

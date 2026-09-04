"""Seam between the stage orchestrator and one pipeline stage implementation."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from arxiv_int.interfaces.stores import DatasetRef

StageOutcome = Literal["completed", "skipped", "failed"]


@dataclass(frozen=True, slots=True)
class StageContext:
    """Everything one stage needs, resolved before the stage starts."""

    stage: str
    run_id: str
    archive_dir: Path
    results_dir: Path
    options: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class StageResult:
    """What one stage produced, reported without reading the artifacts again."""

    stage: str
    outcome: StageOutcome
    detail: str
    outputs: tuple[DatasetRef, ...] = ()


@runtime_checkable
class StageRunner(Protocol):
    """Run one restartable stage over a declared archive and results root."""

    stage: str
    feature: str
    depends_on: tuple[str, ...]

    def run(self, context: StageContext) -> StageResult:
        """Run the stage and report its outcome and published outputs."""

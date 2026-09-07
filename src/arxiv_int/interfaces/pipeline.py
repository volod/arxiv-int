"""Seam between the stage orchestrator and one pipeline stage implementation."""

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol, runtime_checkable

from arxiv_int.interfaces.sources import SiloRoot, SourceOccurrence
from arxiv_int.interfaces.stores import DatasetRef, TransformationRunRef, ValidationResultRef
from arxiv_int.interfaces.tokens import freeze_str_mapping, require_token

StageOutcome = Literal["produced", "partial", "empty", "failed", "not-selected"]


@dataclass(frozen=True, slots=True)
class StageContext:
    """Everything one stage needs, resolved before the stage starts."""

    stage: str
    run_id: str
    generation_id: str
    silos: tuple[SiloRoot, ...]
    results_dir: Path
    options: Mapping[str, str]

    def __post_init__(self) -> None:
        require_token(self.stage, "stage")
        require_token(self.run_id, "run_id")
        require_token(self.generation_id, "generation_id")
        if not self.silos:
            raise ValueError("silos must contain at least one archive root")
        ids = [silo.silo_id for silo in self.silos]
        if len(ids) != len(set(ids)):
            raise ValueError("silo_id values must be unique within one stage context")
        object.__setattr__(self, "options", freeze_str_mapping(self.options))

    def silo_root(self, silo_id: str) -> Path:
        """Return the local root for one declared silo id."""
        for silo in self.silos:
            if silo.silo_id == silo_id:
                return silo.root
        known = ", ".join(silo.silo_id for silo in self.silos)
        raise LookupError(f"unknown silo_id '{silo_id}'; declared silos are {known}")

    def source_path(self, occurrence: SourceOccurrence) -> Path:
        """Resolve one occurrence against its silo without reading the file."""
        return occurrence.resolve(self.silo_root(occurrence.silo_id))


@dataclass(frozen=True, slots=True)
class StageResult:
    """What one stage produced, reported without reading the artifacts again."""

    stage: str
    outcome: StageOutcome
    detail: str
    outputs: tuple[DatasetRef, ...] = ()
    validations: tuple[ValidationResultRef, ...] = ()
    transformations: tuple[TransformationRunRef, ...] = ()


@runtime_checkable
class StageRunner(Protocol):
    """Run one restartable stage over declared archive silos and a results root."""

    stage: str
    feature: str
    depends_on: tuple[str, ...]

    def run(self, context: StageContext) -> StageResult:
        """Run the stage and report its outcome and published outputs."""

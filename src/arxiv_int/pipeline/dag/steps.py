"""Step timing and partial-result preservation."""

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Literal

StepOutcome = Literal["completed", "failed"]


@dataclass(frozen=True, slots=True)
class StepRecord:
    """Durable in-memory result metadata for one attempted step."""

    outcome: StepOutcome
    elapsed_seconds: float
    detail: str = ""


class StepRecorder:
    """Time steps while preserving earlier results when a later step fails."""

    def __init__(self, clock: Callable[[], float] = time.monotonic) -> None:
        self._clock = clock
        self._records: dict[str, StepRecord] = {}
        self._results: dict[str, object] = {}

    @property
    def records(self) -> Mapping[str, StepRecord]:
        return MappingProxyType(self._records)

    @property
    def results(self) -> Mapping[str, object]:
        return MappingProxyType(self._results)

    def run(self, step: str, operation: Callable[[], object]) -> object:
        started = self._clock()
        try:
            result = operation()
        except Exception as error:
            self._records[step] = StepRecord(
                outcome="failed",
                elapsed_seconds=max(0.0, self._clock() - started),
                detail=str(error),
            )
            raise
        self._results[step] = result
        self._records[step] = StepRecord(
            outcome="completed",
            elapsed_seconds=max(0.0, self._clock() - started),
        )
        return result

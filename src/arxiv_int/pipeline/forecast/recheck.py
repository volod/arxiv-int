"""Stage-boundary free-space recheck before allocation."""

from collections.abc import Callable
from pathlib import Path

from arxiv_int.pipeline.forecast.errors import ForecastRefusedError
from arxiv_int.pipeline.forecast.model import DeviceBudget, ForecastDocument
from arxiv_int.runtime.filesystem import FilesystemEvidence, inspect_filesystem

Inspector = Callable[[Path], FilesystemEvidence]


def make_space_guard(
    document: ForecastDocument,
    inspector: Inspector | None = None,
) -> Callable[[str], None]:
    """Return a callback that blocks the next stage when free space falls below reserve."""
    probe = inspector or inspect_filesystem

    def guard(stage: str) -> None:
        recheck_free_space(document, probe, stage)

    return guard


def recheck_free_space(
    document: ForecastDocument,
    inspector: Inspector,
    stage: str,
) -> None:
    """Refuse allocation when a device no longer holds peak plus hard reserve."""
    for budget in document.devices:
        if _is_source_only(budget):
            continue
        if not budget.accessible or not budget.path:
            raise ForecastRefusedError(
                f"stage {stage} blocked: device {budget.device_id} is inaccessible"
            )
        try:
            evidence = inspector(Path(budget.path))
        except OSError as error:
            raise ForecastRefusedError(
                f"stage {stage} blocked: device {budget.device_id} is inaccessible"
            ) from error
        needed = budget.peak.upper + budget.reserve_bytes
        if evidence.free_bytes < needed:
            raise ForecastRefusedError(
                f"stage {stage} blocked: device {budget.device_id} free {evidence.free_bytes} "
                f"below peak {budget.peak.upper} plus reserve {budget.reserve_bytes}"
            )


def _is_source_only(budget: DeviceBudget) -> bool:
    return budget.storage_classes == ("source",)

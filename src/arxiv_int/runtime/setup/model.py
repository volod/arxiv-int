"""Typed setup attempt, phase, and report values."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

PhaseName = Literal[
    "config",
    "env",
    "package",
    "paths",
    "postgres-image",
    "images",
    "models",
    "services",
    "wait",
    "contracts",
    "schema",
    "readiness",
]
PhaseStatus = Literal["ready", "reused", "blocked", "degraded", "skipped", "cancelled"]
SetupStatus = Literal["ready", "blocked", "degraded", "cancelled"]
ProviderStatus = Literal["ready", "blocked", "unavailable"]

RETRY_COMMAND = "make setup"
PHASE_ORDER: tuple[PhaseName, ...] = (
    "config",
    "env",
    "package",
    "paths",
    "postgres-image",
    "images",
    "models",
    "services",
    "wait",
    "contracts",
    "schema",
    "readiness",
)
ATOMIC_PHASES: dict[str, PhaseName] = {
    "config": "config",
    "env": "env",
    "images": "images",
    "models": "models",
    "wait": "wait",
    "schema": "schema",
}


@dataclass(frozen=True, slots=True)
class PhaseResult:
    """One phase outcome with a redacted next action."""

    name: PhaseName
    status: PhaseStatus
    detail: str
    action: str | None = None
    fingerprint: str = ""

    @property
    def ok(self) -> bool:
        return self.status in {"ready", "reused", "skipped"}


def reused_or_ready(
    verified: dict[str, str] | None, name: PhaseName, fingerprint: str
) -> PhaseStatus:
    """Return reused when the current fingerprint matches stored work."""
    if verified and fingerprint and verified.get(name) == fingerprint:
        return "reused"
    return "ready"


@dataclass(frozen=True, slots=True)
class SetupReport:
    """Redacted aggregate setup result written under RESULTS_DIR when roots are safe."""

    attempt_id: str
    status: SetupStatus
    phases: tuple[PhaseResult, ...]
    infrastructure: SetupStatus
    pipeline_implementation: ProviderStatus
    next_action: str
    retry_command: str = RETRY_COMMAND
    report_path: Path | None = None
    log_dir: Path | None = None

    @property
    def exit_code(self) -> int:
        return {"ready": 0, "blocked": 1, "degraded": 2, "cancelled": 1}[self.status]

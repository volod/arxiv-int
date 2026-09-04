"""Typed preflight findings.

Adapted under the MIT License from https://github.com/volod/selfsuvis at revision
bd0f4447bf20a72e9421c93f208ce1f52f1c622b.
"""

from dataclasses import dataclass
from typing import Literal

CheckStatus = Literal["ready", "degraded", "blocked"]


@dataclass(frozen=True, slots=True)
class PreflightFinding:
    """One named readiness result with an operator-facing explanation."""

    name: str
    status: CheckStatus
    detail: str


class PreflightReport:
    """Collect all readiness findings instead of failing on the first one."""

    def __init__(self, scope: str) -> None:
        self.scope = scope
        self._findings: list[PreflightFinding] = []

    @property
    def findings(self) -> tuple[PreflightFinding, ...]:
        return tuple(self._findings)

    @property
    def status(self) -> CheckStatus:
        statuses = {finding.status for finding in self._findings}
        if "blocked" in statuses:
            return "blocked"
        if "degraded" in statuses:
            return "degraded"
        return "ready"

    def add(self, name: str, status: CheckStatus, detail: str) -> None:
        self._findings.append(PreflightFinding(name=name, status=status, detail=detail))

    def require_ready(self) -> None:
        blocked = [finding for finding in self._findings if finding.status == "blocked"]
        if not blocked:
            return
        details = "\n".join(f"- {finding.name}: {finding.detail}" for finding in blocked)
        raise RuntimeError(f"{self.scope} preflight blocked:\n{details}")

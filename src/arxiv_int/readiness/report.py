"""Typed preflight findings and safe report rendering."""

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

CheckStatus = Literal["ready", "degraded", "blocked"]

_STATUS_COLORS = {"degraded": "\033[33m", "blocked": "\033[31m"}
_COLOR_RESET = "\033[0m"
_SECTIONS = {
    "tool": "Environment and tools",
    "resource": "Host resources",
    "config": "Configuration",
    "path": "Storage",
    "paths": "Storage",
    "service": "Services",
    "services": "Services",
    "database": "Database",
    "contracts": "Contracts",
    "inference": "Inference",
    "report": "Report persistence",
}


@dataclass(frozen=True, slots=True)
class PreflightFinding:
    """One named readiness result with an operator-facing explanation."""

    name: str
    status: CheckStatus
    detail: str
    action: str | None = None


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

    @property
    def exit_code(self) -> int:
        """Return a distinct process status for every aggregate state."""
        return {"ready": 0, "blocked": 1, "degraded": 2}[self.status]

    def add(
        self,
        name: str,
        status: CheckStatus,
        detail: str,
        *,
        action: str | None = None,
    ) -> None:
        self._findings.append(
            PreflightFinding(name=name, status=status, detail=detail, action=action)
        )

    def extend(self, findings: tuple[PreflightFinding, ...]) -> None:
        """Append already evaluated findings without losing their actions."""
        self._findings.extend(findings)

    def console_lines(self, *, color: bool = False) -> tuple[str, ...]:
        """Render a stable, human-readable report."""
        lines = [f"readiness: {self.status} ({len(self._findings)} checks)"]
        previous_section = ""
        for finding in self._findings:
            section = _SECTIONS.get(finding.name.partition(".")[0], "Storage")
            if section != previous_section:
                lines.extend(("", f"--- {section} ---"))
                previous_section = section
            line = f"[{finding.status.upper()}] {finding.name}: {finding.detail}"
            escape = _STATUS_COLORS.get(finding.status) if color else None
            lines.append(f"{escape}{line}{_COLOR_RESET}" if escape else line)
            if finding.action:
                lines.append(f"  next: {finding.action}")
        return tuple(lines)

    def as_dict(self, *, generated_at: datetime | None = None) -> dict[str, object]:
        """Return the redaction-safe JSON representation."""
        timestamp = generated_at or datetime.now(UTC)
        return {
            "schema_version": 1,
            "generated_at": timestamp.isoformat(),
            "scope": self.scope,
            "status": self.status,
            "exit_code": self.exit_code,
            "findings": [
                {
                    "name": item.name,
                    "status": item.status,
                    "detail": item.detail,
                    "action": item.action,
                }
                for item in self._findings
            ],
        }

    def write_json(self, destination: Path) -> Path:
        """Atomically persist a report with owner-only permissions."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        descriptor, raw_path = tempfile.mkstemp(
            dir=destination.parent, prefix=f".{destination.name}.", text=True
        )
        temporary = Path(raw_path)
        try:
            os.fchmod(descriptor, 0o600)
            with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                json.dump(self.as_dict(), stream, indent=2, sort_keys=True)
                stream.write("\n")
            temporary.replace(destination)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return destination

    def require_ready(self) -> None:
        blocked = [finding for finding in self._findings if finding.status == "blocked"]
        if not blocked:
            return
        details = "\n".join(f"- {finding.name}: {finding.detail}" for finding in blocked)
        raise RuntimeError(f"{self.scope} preflight blocked:\n{details}")

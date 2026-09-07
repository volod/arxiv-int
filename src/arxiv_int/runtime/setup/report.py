"""Redacted setup report persistence using the shared containment policy."""

import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.readiness.run import _destination_refusal
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.setup.model import PhaseResult, SetupReport, SetupStatus

DEFAULT_REPORT_NAME = "setup.json"


def _phase_dict(result: PhaseResult) -> dict[str, object]:
    return {
        "name": result.name,
        "status": result.status,
        "detail": result.detail,
        "action": result.action,
        "fingerprint": result.fingerprint,
    }


def report_payload(
    report: SetupReport, *, generated_at: datetime | None = None
) -> dict[str, object]:
    """Return the JSON object written to RESULTS_DIR/reports/setup.json."""
    timestamp = generated_at or datetime.now(UTC)
    return {
        "schema_version": 1,
        "generated_at": timestamp.isoformat(),
        "attempt_id": report.attempt_id,
        "status": report.status,
        "exit_code": report.exit_code,
        "infrastructure": report.infrastructure,
        "pipeline_implementation": report.pipeline_implementation,
        "next_action": report.next_action,
        "retry_command": report.retry_command,
        "phases": [_phase_dict(item) for item in report.phases],
    }


def persist_setup_report(report: SetupReport, config: RuntimeConfig | None) -> Path | None:
    """Write the setup report only after safe product roots exist."""
    if config is None:
        return None
    destination = config.results_dir / "reports" / DEFAULT_REPORT_NAME
    resolved = destination.resolve()
    refusal = _destination_refusal(config, resolved)
    if refusal is not None:
        return None
    resolved.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(
        dir=resolved.parent, prefix=f".{resolved.name}.", text=True
    )
    temporary = Path(raw_path)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(report_payload(report), stream, indent=2, sort_keys=True)
            stream.write("\n")
        temporary.replace(resolved)
    except OSError:
        temporary.unlink(missing_ok=True)
        return None
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return resolved


def console_lines(report: SetupReport) -> tuple[str, ...]:
    """Render per-phase status and the next retry command."""
    lines = [
        f"setup: {report.status} (attempt {report.attempt_id})",
        f"infrastructure: {report.infrastructure}",
        f"pipeline_implementation: {report.pipeline_implementation}",
    ]
    for result in report.phases:
        lines.append(f"[{result.status.upper()}] {result.name}: {result.detail}")
        if result.action:
            lines.append(f"  next: {result.action}")
    lines.append(f"next: {report.next_action}")
    return tuple(lines)


def aggregate_status(phases: tuple[PhaseResult, ...]) -> SetupStatus:
    """Collapse phase statuses; cancelled and blocked win over degraded."""
    statuses = {item.status for item in phases}
    if "cancelled" in statuses:
        return "cancelled"
    if "blocked" in statuses:
        return "blocked"
    if "degraded" in statuses:
        return "degraded"
    return "ready"

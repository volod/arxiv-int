"""CLI helpers for the project-owned PostgreSQL image."""

import json
import logging
from pathlib import Path

from arxiv_int.stores.postgres_image.build import build_postgres_image
from arxiv_int.stores.postgres_image.compatibility import write_age_compatibility
from arxiv_int.stores.postgres_image.pins import load_image_pins
from arxiv_int.stores.postgres_image.probes import run_extension_probes

_LOG = logging.getLogger(__name__)


def run_build_command(project_root: Path, *, no_cache: bool) -> int:
    """Build the pinned image; return a process exit code."""
    pins = build_postgres_image(project_root, no_cache=no_cache)
    print(pins.local_image_ref)
    return 0


def run_probe_command(project_root: Path, pgdata_dir: Path, *, write_gate: bool) -> int:
    """Run disposable extension probes and optionally record the AGE gate."""
    pins = load_image_pins(project_root)
    report = run_extension_probes(project_root, pgdata_dir, pins=pins)
    payload = {
        "image_ref": report.image_ref,
        "age_compatible": report.age_compatible,
        "summary": report.summary,
    }
    print(json.dumps(payload, indent=2, sort_keys=True))
    if write_gate:
        if report.age_compatible:
            write_age_compatibility(
                project_root,
                age_enabled=True,
                reason="combined extension probes passed",
                image_ref=report.image_ref,
                probe_summary=report.summary,
            )
        else:
            reason = report.summary.get("age_gate", "AGE compatibility probes failed")
            write_age_compatibility(
                project_root,
                age_enabled=False,
                reason=reason,
                image_ref=report.image_ref,
                probe_summary=report.summary,
            )
            _LOG.warning("AGE profile disabled: %s", reason)
    core_ok = report.all_core_passed and any(
        item.name == "start" and item.ok for item in report.results
    )
    if not core_ok:
        return 1
    # AGE failure is a valid negative when the gate is written; core still succeeded.
    if not report.age_compatible and not write_gate:
        return 2
    return 0

"""AGE compatibility gate recorded beside the image definition."""

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from arxiv_int.stores.postgres_image.pins import postgres_dir


@dataclass(frozen=True, slots=True)
class AgeCompatibility:
    """Whether the graph profile may require Apache AGE."""

    age_enabled: bool
    reason: str
    image_ref: str
    probed_at: str
    probe_summary: dict[str, str]


def compatibility_path(project_root: Path) -> Path:
    return postgres_dir(project_root) / "age-compatibility.json"


def load_age_compatibility(project_root: Path) -> AgeCompatibility:
    """Load the committed compatibility record; missing file means AGE not yet proven."""
    path = compatibility_path(project_root)
    if not path.is_file():
        return AgeCompatibility(
            age_enabled=False,
            reason="AGE compatibility suite has not been recorded yet",
            image_ref="",
            probed_at="",
            probe_summary={},
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    summary = payload.get("probe_summary") or {}
    if not isinstance(summary, dict):
        raise ValueError("age-compatibility.json probe_summary must be an object")
    return AgeCompatibility(
        age_enabled=bool(payload.get("age_enabled")),
        reason=str(payload.get("reason") or ""),
        image_ref=str(payload.get("image_ref") or ""),
        probed_at=str(payload.get("probed_at") or ""),
        probe_summary={str(key): str(value) for key, value in summary.items()},
    )


def write_age_compatibility(
    project_root: Path,
    *,
    age_enabled: bool,
    reason: str,
    image_ref: str,
    probe_summary: dict[str, str],
) -> AgeCompatibility:
    """Persist the compatibility decision next to the Dockerfile."""
    record = AgeCompatibility(
        age_enabled=age_enabled,
        reason=reason,
        image_ref=image_ref,
        probed_at=datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        probe_summary=dict(probe_summary),
    )
    path = compatibility_path(project_root)
    path.write_text(
        json.dumps(
            {
                "age_enabled": record.age_enabled,
                "reason": record.reason,
                "image_ref": record.image_ref,
                "probed_at": record.probed_at,
                "probe_summary": record.probe_summary,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return record

"""Immutable runtime configuration values."""

import re
from dataclasses import dataclass, field
from pathlib import Path

_SENSITIVE = re.compile(r"(?:PASSWORD|SECRET|TOKEN|DATABASE_URL)")


@dataclass(frozen=True, slots=True)
class ArchiveSilo:
    """One stable source-silo identity and its resolved root."""

    silo_id: str
    variable: str
    root: Path


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    """Resolved runtime roots and values used by every operator command."""

    project_root: Path
    archive_silos: tuple[ArchiveSilo, ...]
    results_dir: Path
    pgdata_dir: Path
    runs_dir: Path
    dev_results_dir: Path
    service_state_dir: Path
    model_cache_dir: Path
    tmp_dir: Path
    proof_archive_dir: Path | None
    dev_archive_dir: Path | None
    pg_wal_dir: Path | None
    pg_tablespaces: tuple[tuple[str, Path], ...]
    data_dir: Path
    values: tuple[tuple[str, str], ...] = field(repr=False)

    def rendered(self, *, redact: bool = True) -> tuple[str, ...]:
        """Render stable key/value lines without exposing secrets."""
        lines: list[str] = []
        for name, value in self.values:
            shown = "<redacted>" if redact and _SENSITIVE.search(name) else value
            lines.append(f"{name}={shown}")
        return tuple(lines)

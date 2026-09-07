"""Configured runtime-root placements and validation results."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from arxiv_int.readiness.report import PreflightReport
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.filesystem import FilesystemEvidence

StorageClass = Literal["source", "bulk", "database", "scratch", "model", "service-state"]


@dataclass(frozen=True, slots=True)
class RootPlacement:
    """One configured root and its required storage class."""

    variable: str
    path: Path
    storage_class: StorageClass
    output: bool


@dataclass(frozen=True, slots=True)
class PathValidation:
    """All path evidence plus the accumulated readiness report."""

    placements: tuple[tuple[RootPlacement, FilesystemEvidence], ...]
    report: PreflightReport


def runtime_placements(config: RuntimeConfig) -> tuple[RootPlacement, ...]:
    """Return every independently configured root and its storage contract."""
    placements = [
        *(
            RootPlacement(silo.variable, silo.root, "source", False)
            for silo in config.archive_silos
        ),
        RootPlacement("RESULTS_DIR", config.results_dir, "bulk", True),
        RootPlacement("PGDATA_DIR", config.pgdata_dir, "database", True),
        RootPlacement("RUNS_DIR", config.runs_dir, "bulk", True),
        RootPlacement("SERVICE_STATE_DIR", config.service_state_dir, "service-state", True),
        RootPlacement("MODEL_CACHE_DIR", config.model_cache_dir, "model", True),
        RootPlacement("TMP_DIR", config.tmp_dir, "scratch", True),
    ]
    if config.pg_wal_dir is not None:
        placements.append(RootPlacement("PG_WAL_DIR", config.pg_wal_dir, "database", True))
    placements.extend(
        RootPlacement(f"PG_TABLESPACE_{name.upper()}_DIR", path, "database", True)
        for name, path in config.pg_tablespaces
    )
    return tuple(placements)

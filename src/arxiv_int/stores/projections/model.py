"""Typed identities for one rebuildable search or graph projection run."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

KIND_LEXICAL = "lexical"
KIND_VECTOR = "vector"
KIND_GRAPH = "graph"
KINDS = (KIND_LEXICAL, KIND_VECTOR, KIND_GRAPH)

STATUS_STAGING = "staging"
STATUS_VALIDATED = "validated"
STATUS_ACTIVE = "active"
STATUS_FAILED = "failed"
STATUS_RETIRED = "retired"
STATUS_DROPPED = "dropped"

ENGINE_PARADEDB = "paradedb"
ENGINE_PGVECTOR = "pgvector"
ENGINE_AGE = "age"
ENGINE_RECURSIVE_SQL = "recursive-sql"

SCHEMA_VERSION = "1.0.0"

RUN_OK = "ok"
RUN_FAILED = "failed"
RUN_NOT_RUN = "not-run"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_RUN = 2

DEFAULT_SAMPLE_LIMIT = 8
DEFAULT_WALK_DEPTH = 2


@dataclass(frozen=True, slots=True)
class ProjectionRequest:
    """Inputs for one projection build, switch, or cleanup run."""

    run_id: str
    project_root: Path
    kinds: tuple[str, ...] = KINDS
    database_url: str | None = None
    activate: bool = False
    publish: bool = False
    runs_dir: Path | None = None
    age_enabled: bool | None = None
    skip_dbt: bool = False
    apply_cleanup: bool = False
    threads: int = 2


@dataclass(frozen=True, slots=True)
class KindBuild:
    """Secret-free outcome for one kind in a versioned build."""

    kind: str
    projection_id: str
    version_id: str
    status: str
    engine: str
    engine_object: str
    row_count: int
    checksum: str
    quality_status: str
    publishable: bool
    logical_ids: tuple[str, ...]
    detail: str


@dataclass(frozen=True, slots=True)
class ProjectionResult:
    """Secret-free lifecycle outcome retained under DATA_DIR and optional RUNS_DIR."""

    status: str
    command: str
    run_id: str
    version_id: str
    activatable: bool
    activated: bool
    detail: str
    artifact_dir: str
    kinds: tuple[KindBuild, ...] = ()
    cleanup_plan: tuple[Mapping[str, Any], ...] = ()
    published_manifest_dir: str | None = None

    @property
    def ok(self) -> bool:
        """Return whether every requested kind validated."""
        return self.status == RUN_OK

    def as_json_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping with no credential fields."""
        return {
            "activatable": self.activatable,
            "activated": self.activated,
            "artifactDir": self.artifact_dir,
            "cleanupPlan": [dict(item) for item in self.cleanup_plan],
            "command": self.command,
            "detail": self.detail,
            "kinds": [_kind_json(item) for item in self.kinds],
            "publishedManifestDir": self.published_manifest_dir,
            "runId": self.run_id,
            "status": self.status,
            "versionId": self.version_id,
        }


def exit_status(result: ProjectionResult) -> int:
    """Map a typed result onto a process status."""
    if result.status == RUN_OK:
        return EXIT_OK
    if result.status == RUN_NOT_RUN:
        return EXIT_NOT_RUN
    return EXIT_FAILED


def requested_kinds(values: Sequence[str] | None) -> tuple[str, ...]:
    """Normalize kind arguments, rejecting unknown values."""
    if not values:
        return KINDS
    ordered: list[str] = []
    for item in values:
        kind = item.strip().lower()
        if kind == "all":
            return KINDS
        if kind not in KINDS:
            raise ValueError(f"unknown projection kind {item!r}")
        if kind not in ordered:
            ordered.append(kind)
    return tuple(ordered)


def _kind_json(item: KindBuild) -> dict[str, Any]:
    return {
        "checksum": item.checksum,
        "detail": item.detail,
        "engine": item.engine,
        "engineObject": item.engine_object,
        "kind": item.kind,
        "logicalIds": list(item.logical_ids),
        "projectionId": item.projection_id,
        "publishable": item.publishable,
        "qualityStatus": item.quality_status,
        "rowCount": item.row_count,
        "status": item.status,
        "versionId": item.version_id,
    }

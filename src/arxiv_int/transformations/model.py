"""Typed identities for one dbt parse, compile, build, or test invocation."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_NOT_RUN = "not-run"
COMMANDS = ("parse", "compile", "build", "test")
DEFAULT_SELECT = ("tag:fixture", "tag:quality")
MAX_THREADS = 4
DEFAULT_THREADS = 2
DEFAULT_POLICY_VERSION = "1"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_RUN = 2


@dataclass(frozen=True, slots=True)
class TransformRequest:
    """Inputs for one rooted dbt invocation."""

    command: str
    run_id: str
    project_root: Path
    database_url: str | None = None
    select: tuple[str, ...] = DEFAULT_SELECT
    threads: int = DEFAULT_THREADS
    full_refresh: bool = False
    fail_tests: bool = False
    policy_version: str = DEFAULT_POLICY_VERSION
    activate: bool = False
    publish: bool = False
    runs_dir: Path | None = None
    vars: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class TransformResult:
    """Secret-free outcome the pipeline may activate only when tests passed."""

    status: str
    command: str
    run_id: str
    generation_id: str
    activatable: bool
    detail: str
    artifact_dir: str
    selected: tuple[str, ...]
    input_fingerprint: str
    model_fingerprint: str
    rule_outcomes: tuple[Mapping[str, Any], ...] = ()
    relation_names: tuple[str, ...] = ()
    row_counts: Mapping[str, int] = field(default_factory=dict)
    published_manifest_dir: str | None = None
    published_quality_dir: str | None = None

    @property
    def ok(self) -> bool:
        """Return whether the invocation completed successfully."""
        return self.status == STATUS_OK

    def as_json_dict(self) -> dict[str, Any]:
        """Return a JSON-ready mapping with no credential fields."""
        return {
            "activatable": self.activatable,
            "artifactDir": self.artifact_dir,
            "command": self.command,
            "detail": self.detail,
            "generationId": self.generation_id,
            "inputFingerprint": self.input_fingerprint,
            "modelFingerprint": self.model_fingerprint,
            "publishedManifestDir": self.published_manifest_dir,
            "publishedQualityDir": self.published_quality_dir,
            "relationNames": list(self.relation_names),
            "rowCounts": dict(self.row_counts),
            "ruleOutcomes": [dict(item) for item in self.rule_outcomes],
            "runId": self.run_id,
            "selected": list(self.selected),
            "status": self.status,
        }


def exit_status(result: TransformResult) -> int:
    """Map a typed result onto a process status."""
    if result.status == STATUS_OK:
        return EXIT_OK
    if result.status == STATUS_NOT_RUN:
        return EXIT_NOT_RUN
    return EXIT_FAILED


def required_database(command: str) -> bool:
    """Report whether the command materializes or tests against PostgreSQL."""
    return command in {"build", "test"}

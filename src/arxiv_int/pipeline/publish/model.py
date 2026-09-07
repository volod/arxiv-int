"""Typed knowledge-base document, profile families, and logical run statuses."""

from dataclasses import dataclass

SCHEMA_ID = "arxiv-int.knowledge-base.v1"
PROFILE_SCHEMA = "arxiv-int.pipeline.profile.v1"
STATUSES = ("succeeded", "partial", "failed", "blocked", "interrupted")
EXIT_BY_STATUS = {
    "succeeded": 0,
    "partial": 2,
    "failed": 1,
    "blocked": 3,
    "interrupted": 130,
}
KNOWLEDGE_BASE_NAME = "knowledge-base.json"
REPORT_HTML = "reports/index.html"
REPORT_JSON = "reports/report.json"
ACTIVE_GENERATION = "active-generation.json"
ACTIVE_CATALOG = "active-catalog.json"


@dataclass(frozen=True, slots=True)
class OutputFamily:
    """One named output family produced by a stage."""

    family_id: str
    stage: str
    required: bool
    path: str = ""


@dataclass(frozen=True, slots=True)
class PipelineProfile:
    """Requested stages and output families for one pipeline profile."""

    name: str
    required_stages: tuple[str, ...]
    optional_stages: tuple[str, ...]
    families: tuple[OutputFamily, ...]
    report_family: str = "report"


@dataclass(frozen=True, slots=True)
class OutputEntry:
    """One sealed family: path, checksum, counts, and honest outcome."""

    family: str
    stage: str
    path: str
    checksum: str
    bytes: int
    row_count: int | None
    outcome: str
    required: bool


@dataclass(frozen=True, slots=True)
class Coverage:
    """Denominators for required versus produced families."""

    required_families: int
    produced: int
    empty: int
    partial: int
    failed: int
    missing: int
    not_selected: int


@dataclass(frozen=True, slots=True)
class KnowledgeBase:
    """Fingerprinted generation manifest retained under a run id."""

    schema: str
    run_id: str
    generation_id: str
    profile: str
    status: str
    active: bool
    source_snapshot: str
    config_fingerprint: str
    fingerprint: str
    outputs: tuple[OutputEntry, ...]
    coverage: Coverage
    limitations: tuple[str, ...]
    not_selected: tuple[str, ...]
    report_path: str
    status_command: str
    resume_command: str
    catalog_path: str

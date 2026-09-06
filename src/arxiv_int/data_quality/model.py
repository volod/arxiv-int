"""Typed quality identities, statuses, and result values with no optional imports."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_WARNING = "warning"
STATUS_NOT_APPLICABLE = "not-applicable"
STATUS_NOT_RUN = "not-run"
STATUSES = frozenset(
    {STATUS_PASS, STATUS_FAIL, STATUS_WARNING, STATUS_NOT_APPLICABLE, STATUS_NOT_RUN}
)

SCOPE_BATCH = "batch"
SCOPE_SNAPSHOT = "snapshot"

BACKEND_PANDERA = "pandera"
BACKEND_DBT = "dbt"
BACKEND_DISK = "disk"
BACKEND_ONTOLOGY = "ontology"

KIND_TYPE = "type"
KIND_NULLABILITY = "nullability"
KIND_MAX_LENGTH = "max_length"
KIND_DECIMAL = "decimal"
KIND_ACCEPTED_VALUES = "accepted_values"
KIND_UNIT = "unit"
KIND_BATCH_UNIQUE = "batch_unique"
KIND_UNIQUE = "unique"
KIND_RELATIONSHIP = "relationship"
KIND_SEMANTIC = "semantic"

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"

VALIDATION_DEPTH_DATA = "data"
VALIDATION_DEPTH_SCHEMA_ONLY = "schema-only"

RULE_CATALOG_VERSION = "1.0.0"

TOOL_PANDERA = "pandera"
TOOL_POLARS = "polars"
TOOL_PYARROW = "pyarrow"
TOOL_DISK = "disk-backed"

_SENSITIVE_MARKERS = ("password", "secret", "token", "credential", "api_key")


@dataclass(frozen=True, slots=True)
class QualityRule:
    """One contract-derived check with a stable identity and backend mapping."""

    rule_id: str
    kind: str
    scope: str
    backend: str
    severity: str
    required: bool
    description: str
    column: str | None = None
    logical_type: str | None = None
    max_length: int | None = None
    precision: int | None = None
    scale: int | None = None
    accepted_values: tuple[str, ...] = ()
    unit_column: str | None = None
    target_contract_id: str | None = None
    target_schema: str | None = None
    target_table: str | None = None
    target_column: str | None = None
    disk_backend: str | None = None
    dbt_test: str | None = None
    version: str = RULE_CATALOG_VERSION


@dataclass(frozen=True, slots=True)
class RuleCatalog:
    """Compiled checks for one contract, retaining source descriptions."""

    contract_id: str
    odcs_id: str
    version: str
    description: str | None
    schema_name: str
    table_name: str
    primary_key: tuple[str, ...]
    rules: tuple[QualityRule, ...]
    catalog_version: str = RULE_CATALOG_VERSION

    def required_rules(self) -> tuple[QualityRule, ...]:
        """Return required checks in catalog order."""
        return tuple(rule for rule in self.rules if rule.required)

    def by_id(self) -> Mapping[str, QualityRule]:
        """Index rules by stable id."""
        return {rule.rule_id: rule for rule in self.rules}


@dataclass(frozen=True, slots=True)
class FailureSample:
    """One redacted row/column reference for a failed check."""

    row_ref: str
    column: str | None
    value: str
    reason: str


@dataclass(frozen=True, slots=True)
class CheckResult:
    """Outcome of one executed, skipped, or missing rule."""

    rule_id: str
    status: str
    scope: str
    severity: str
    checked_count: int
    failed_count: int
    description: str
    backend: str
    tool: str
    reason: str | None = None
    samples: tuple[FailureSample, ...] = ()

    @property
    def executed(self) -> bool:
        """Report whether the check ran against data."""
        return self.status not in {STATUS_NOT_RUN}


@dataclass(frozen=True, slots=True)
class ToolFingerprint:
    """Installed tool identities used for a validation run."""

    names: Mapping[str, str]


@dataclass(frozen=True, slots=True)
class ValidationLimits:
    """Declared memory and sample bounds for one run."""

    batch_rows: int = 50_000
    spill_bytes: int = 64 * 1024 * 1024
    failure_samples: int = 5
    min_rows: int = 0
    value_chars: int = 64


@dataclass(frozen=True, slots=True)
class DatasetValidationResult:
    """Typed dataset outcome that cannot look publishable when required work is missing."""

    contract_id: str
    status: str
    validation_depth: str
    publishable: bool
    checked_rows: int
    input_fingerprint: str
    catalog_fingerprint: str
    tool_fingerprint: ToolFingerprint
    checks: tuple[CheckResult, ...]
    missing_required: tuple[str, ...]
    limits: ValidationLimits
    reason: str | None = None
    artifact_dir: str | None = None

    def as_json_dict(self) -> dict[str, Any]:
        """Return a secret-free, JSON-ready mapping."""
        return {
            "artifactDir": self.artifact_dir,
            "catalogFingerprint": self.catalog_fingerprint,
            "checkedRows": self.checked_rows,
            "checks": [_check_json(item) for item in self.checks],
            "contractId": self.contract_id,
            "inputFingerprint": self.input_fingerprint,
            "limits": {
                "batchRows": self.limits.batch_rows,
                "failureSamples": self.limits.failure_samples,
                "minRows": self.limits.min_rows,
                "spillBytes": self.limits.spill_bytes,
                "valueChars": self.limits.value_chars,
            },
            "missingRequired": list(self.missing_required),
            "publishable": self.publishable,
            "reason": self.reason,
            "status": self.status,
            "toolFingerprint": dict(self.tool_fingerprint.names),
            "validationDepth": self.validation_depth,
        }


def is_sensitive_column(name: str) -> bool:
    """Report whether a column name looks like a secret carrier."""
    lowered = name.lower()
    return any(marker in lowered for marker in _SENSITIVE_MARKERS)


def redact_value(column: str | None, value: object, *, limit: int) -> str:
    """Return a bounded, secret-free display value."""
    if column is not None and is_sensitive_column(column):
        return "<redacted>"
    text = "<null>" if value is None else str(value)
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _check_json(item: CheckResult) -> dict[str, Any]:
    return {
        "backend": item.backend,
        "checkedCount": item.checked_count,
        "description": item.description,
        "failedCount": item.failed_count,
        "reason": item.reason,
        "ruleId": item.rule_id,
        "samples": [
            {
                "column": sample.column,
                "reason": sample.reason,
                "rowRef": sample.row_ref,
                "value": sample.value,
            }
            for sample in item.samples
        ],
        "scope": item.scope,
        "severity": item.severity,
        "status": item.status,
        "tool": item.tool,
    }


@dataclass(frozen=True, slots=True)
class DbtEvidence:
    """Optional whole-relation dbt outcomes supplied by a later runner."""

    rule_results: Mapping[str, CheckResult] = field(default_factory=dict)
    executed: bool = False

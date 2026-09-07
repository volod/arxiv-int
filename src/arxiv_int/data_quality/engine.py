"""Orchestrate batch, snapshot, and attached semantic checks for one dataset."""

import importlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from arxiv_int.data_quality.io import (
    SchemaOnlyValidationError,
    concat_key_frame,
    load_batches,
    refuse_lazyframe,
)
from arxiv_int.data_quality.model import (
    STATUS_FAIL,
    TOOL_DISK,
    TOOL_PANDERA,
    TOOL_POLARS,
    TOOL_PYARROW,
    VALIDATION_DEPTH_DATA,
    VALIDATION_DEPTH_SCHEMA_ONLY,
    CheckResult,
    DatasetValidationResult,
    DbtEvidence,
    RuleCatalog,
    ToolFingerprint,
    ValidationLimits,
)
from arxiv_int.data_quality.paths import quality_artifact_dir
from arxiv_int.data_quality.results import build_result, input_fingerprint
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root


@dataclass(frozen=True, slots=True)
class ValidationRequest:
    """Inputs for one contract dataset validation run."""

    catalog: RuleCatalog
    source: Path | Any
    related: Mapping[str, Path | Any] = field(default_factory=dict)
    limits: ValidationLimits = field(default_factory=ValidationLimits)
    execute_snapshot: bool = True
    dbt_evidence: DbtEvidence | None = None
    attached: tuple[CheckResult, ...] = ()
    run_id: str | None = None
    project_root: Path | None = None


def _module_version(name: str) -> str:
    try:
        module = importlib.import_module(name)
    except ImportError:
        return "missing"
    return str(getattr(module, "__version__", "unknown"))


def tool_fingerprint() -> ToolFingerprint:
    """Record installed tool versions used by a run."""
    return ToolFingerprint(
        {
            TOOL_PANDERA: _module_version("pandera"),
            TOOL_POLARS: _module_version("polars"),
            TOOL_PYARROW: _module_version("pyarrow"),
            TOOL_DISK: "1.0.0",
        }
    )


def _input_parts(source: Path | Any, related: Mapping[str, Path | Any]) -> tuple[str, ...]:
    parts = ["source:" + (source.name if isinstance(source, Path) else "frame")]
    for name in sorted(related):
        value = related[name]
        parts.append(f"related:{name}:{value.name if isinstance(value, Path) else 'frame'}")
    return tuple(parts)


def _parent_keys(source: Path | Any, column: str, limits: ValidationLimits) -> Any:
    batches = load_batches(source, limits)
    return concat_key_frame(batches, (column,))


def _related_frames(
    catalog: RuleCatalog, related: Mapping[str, Path | Any], limits: ValidationLimits
) -> dict[str, Any]:
    frames: dict[str, Any] = {}
    for name, source in related.items():
        try:
            refuse_lazyframe(source)
        except SchemaOnlyValidationError:
            continue
        target_column = next(
            (
                rule.target_column
                for rule in catalog.rules
                if rule.target_contract_id == name and rule.target_column
            ),
            None,
        )
        if target_column is None:
            continue
        frames[name] = _parent_keys(source, target_column, limits)
    return frames


def _fail_min_rows(
    result: DatasetValidationResult, row_count: int, minimum: int
) -> DatasetValidationResult:
    return DatasetValidationResult(
        contract_id=result.contract_id,
        status=STATUS_FAIL,
        validation_depth=result.validation_depth,
        publishable=False,
        checked_rows=result.checked_rows,
        input_fingerprint=result.input_fingerprint,
        catalog_fingerprint=result.catalog_fingerprint,
        tool_fingerprint=result.tool_fingerprint,
        checks=result.checks,
        missing_required=result.missing_required,
        limits=result.limits,
        reason=f"insufficient rows: {row_count} < min_rows {minimum}",
        artifact_dir=result.artifact_dir,
    )


def validate_dataset(request: ValidationRequest) -> DatasetValidationResult:
    """Run required checks and return a typed, publication-gated result."""
    limits = request.limits
    catalog = request.catalog
    fingerprint = tool_fingerprint()
    try:
        refuse_lazyframe(request.source)
        batches = load_batches(request.source, limits)
    except SchemaOnlyValidationError as error:
        return build_result(
            catalog,
            request.attached,
            checked_rows=0,
            input_fingerprint_value=input_fingerprint(
                _input_parts(request.source, request.related)
            ),
            tool_fingerprint=fingerprint,
            limits=limits,
            validation_depth=VALIDATION_DEPTH_SCHEMA_ONLY,
            reason=str(error),
        )
    from arxiv_int.data_quality.pandera_checks import run_batch_checks
    from arxiv_int.data_quality.snapshot import run_snapshot_checks

    row_count = sum(int(batch.height) for batch in batches)
    checks: list[CheckResult] = list(run_batch_checks(catalog, batches, limits))
    dbt_results = dict(request.dbt_evidence.rule_results) if request.dbt_evidence else {}
    checks.extend(
        run_snapshot_checks(
            catalog,
            batches,
            related=_related_frames(catalog, request.related, limits),
            spill_dir=_spill_dir(request),
            limits=limits,
            row_count=row_count,
            execute=request.execute_snapshot,
            dbt_results=dbt_results,
        )
    )
    checks.extend(request.attached)
    reason = None
    if limits.min_rows > 0 and 0 < row_count < limits.min_rows:
        reason = f"insufficient rows: {row_count} < min_rows {limits.min_rows}"
    result = build_result(
        catalog,
        checks,
        checked_rows=row_count,
        input_fingerprint_value=input_fingerprint(_input_parts(request.source, request.related)),
        tool_fingerprint=fingerprint,
        limits=limits,
        validation_depth=VALIDATION_DEPTH_DATA,
        reason=reason,
        artifact_dir=str(_spill_dir(request)),
    )
    if limits.min_rows > 0 and row_count < limits.min_rows:
        return _fail_min_rows(result, row_count, limits.min_rows)
    return result


def _spill_dir(request: ValidationRequest) -> Path:
    try:
        root = find_project_root(request.project_root)
    except ProjectRootError:
        root = Path.cwd()
    return quality_artifact_dir(root, request.run_id) / "spill"


def validate_catalogs(
    requests: Sequence[ValidationRequest],
) -> tuple[DatasetValidationResult, ...]:
    """Validate several datasets independently."""
    return tuple(validate_dataset(item) for item in requests)

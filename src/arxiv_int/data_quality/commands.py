"""Operator-facing data-quality check command."""

import json
import logging
from pathlib import Path

from arxiv_int.contracts.catalog.registry import FileRegistry
from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.sqlalchemy.model import load_schema_model
from arxiv_int.data_quality.engine import ValidationRequest, validate_dataset
from arxiv_int.data_quality.engine.model import (
    DatasetValidationResult,
    RuleCatalog,
    ValidationLimits,
)
from arxiv_int.data_quality.engine.paths import published_quality_dir, quality_artifact_dir
from arxiv_int.data_quality.generate import compile_catalogs
from arxiv_int.data_quality.rules import UnsupportedQualityMappingError
from arxiv_int.runtime.project_root import find_project_root

_LOG = logging.getLogger(__name__)


def _write_result(destination: Path, result: DatasetValidationResult) -> Path:
    destination.mkdir(parents=True, exist_ok=True)
    path = destination / "result.json"
    path.write_text(
        json.dumps(result.as_json_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return path


def _log_failures(result: DatasetValidationResult) -> None:
    if result.publishable:
        return
    for item in result.checks:
        if item.status in {"fail", "not-run"}:
            _LOG.error("%s: %s (%s)", item.rule_id, item.status, item.reason or item.description)
    for rule_id in result.missing_required:
        _LOG.error("missing required check: %s", rule_id)


def _publish_if_requested(
    result: DatasetValidationResult, *, publish: bool, runs_dir: Path | None, run_id: str
) -> None:
    if not publish:
        return
    if runs_dir is None:
        _LOG.warning("publish skipped: RUNS_DIR was not provided")
        return
    copied = _write_result(published_quality_dir(runs_dir, run_id), result)
    _LOG.info("published quality evidence: %s", copied)


def _exit_status(result: DatasetValidationResult) -> int:
    if result.publishable:
        return 0
    if result.status == "not-run":
        return 2
    return 1


def _catalog_for(dataset: str, root: Path) -> RuleCatalog:
    contracts_root = contracts_root_for(root)
    registry = FileRegistry(contracts_root)
    if dataset not in set(registry.contract_ids()):
        raise LookupError(f"unknown dataset '{dataset}'")
    model = load_schema_model(registry)
    odcs = {contract_id: registry.load_odcs(contract_id) for contract_id in registry.contract_ids()}
    catalogs = {item.contract_id: item for item in compile_catalogs(model, odcs)}
    return catalogs[dataset]


def run_check(
    dataset: str,
    *,
    run_id: str,
    input_path: Path,
    related: dict[str, Path] | None = None,
    project_root: Path | None = None,
    execute_snapshot: bool = True,
    publish: bool = False,
    runs_dir: Path | None = None,
    limits: ValidationLimits | None = None,
) -> int:
    """Validate one dataset and write secret-free evidence under DATA_DIR."""
    root = find_project_root(project_root)
    try:
        catalog = _catalog_for(dataset, root)
    except LookupError as error:
        _LOG.error("%s", error)
        return 1
    except UnsupportedQualityMappingError as error:
        _LOG.error("%s", error)
        return 1
    result = validate_dataset(
        ValidationRequest(
            catalog=catalog,
            source=input_path,
            related=related or {},
            limits=limits or ValidationLimits(),
            execute_snapshot=execute_snapshot,
            run_id=run_id,
            project_root=root,
        )
    )
    written = _write_result(quality_artifact_dir(root, run_id), result)
    _LOG.info(
        "data-quality %s status=%s publishable=%s rows=%d artifact=%s",
        dataset,
        result.status,
        result.publishable,
        result.checked_rows,
        written,
    )
    _log_failures(result)
    _publish_if_requested(result, publish=publish, runs_dir=runs_dir, run_id=run_id)
    return _exit_status(result)

"""Orchestration for the accumulated workstation readiness report."""

import os
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.readiness.checks import (
    check_password,
    check_resources,
    check_services,
    check_tools,
)
from arxiv_int.readiness.database import check_database
from arxiv_int.readiness.inference import check_contracts, check_inference
from arxiv_int.readiness.probes import LocalProbe, Probe
from arxiv_int.readiness.report import CheckStatus, PreflightFinding, PreflightReport
from arxiv_int.runtime.config import ConfigurationError, load_runtime_config
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.containment import (
    containment_violation,
    contains,
    report_protected_roots,
)
from arxiv_int.runtime.filesystem import FilesystemEvidence, existing_ancestor, inspect_filesystem
from arxiv_int.runtime.paths import validate_runtime_paths
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root
from arxiv_int.runtime.service_plan import ServicePlan, plan_services

DEFAULT_REPORT_NAME = "readiness.json"


@dataclass(frozen=True, slots=True)
class ReadinessResult:
    """A completed report and its optional persisted location."""

    report: PreflightReport
    report_path: Path | None


def run_readiness(
    *,
    project_root: Path | None = None,
    environment: Mapping[str, str] | None = None,
    profiles: str = "pipeline",
    timeout: float = 3.0,
    report_path: Path | None = None,
    persist: bool = True,
    probe: Probe | None = None,
    inspector: Callable[[Path], FilesystemEvidence] = inspect_filesystem,
) -> ReadinessResult:
    """Run every applicable check and persist one redaction-safe JSON report."""
    if timeout <= 0:
        raise ValueError("readiness timeout must be greater than zero")
    active_probe = probe or LocalProbe()
    report = PreflightReport("fresh-copy readiness")
    try:
        root = find_project_root(project_root, environment)
    except ProjectRootError as error:
        report.add(
            "config.root",
            "blocked",
            str(error),
            action="run make targets from a checkout or set PROJECT_ROOT to one",
        )
        return ReadinessResult(report, None)
    check_tools(report, active_probe, root, timeout)
    try:
        plan = plan_services(profiles)
    except ValueError as error:
        report.add(
            "config.profiles",
            "blocked",
            str(error),
            action="set SERVICE_PROFILES to documented profile names",
        )
        plan = plan_services("pipeline")
    check_resources(
        report,
        active_probe,
        root,
        timeout,
        require_gpu="vllm" in plan.services,
    )
    try:
        config = load_runtime_config(project_root=root, environment=environment)
    except ConfigurationError as error:
        report.add(
            "config.runtime",
            "blocked",
            str(error),
            action="copy .env.example to .env and set the required operator roots",
        )
        return ReadinessResult(report, None)
    report.add("config.runtime", "ready", "runtime configuration resolved; secrets are masked")
    if plan.database:
        check_password(report, config)
    _check_paths(report, config, inspector, plan)
    database_healthy = check_services(report, config, plan.profiles, active_probe, timeout)
    check_database(
        report,
        config,
        plan.profiles,
        active_probe,
        timeout,
        database_healthy=database_healthy,
    )
    if plan.pipeline:
        check_contracts(report, config)
    if plan.inference:
        check_inference(report, config, active_probe, timeout, vllm_service="vllm" in plan.services)
    destination = report_path or config.results_dir / "reports" / DEFAULT_REPORT_NAME
    persisted = _persist_report(report, config, destination) if persist else None
    return ReadinessResult(report, persisted)


def _check_paths(
    report: PreflightReport,
    config: RuntimeConfig,
    inspector: Callable[[Path], FilesystemEvidence],
    plan: ServicePlan,
) -> None:
    try:
        validation = validate_runtime_paths(
            config, inspector=inspector, variables=plan.path_variables(config, readiness=True)
        )
    except OSError as error:
        report.add(
            "paths",
            "blocked",
            f"filesystem inspection failed: {error.__class__.__name__}",
            action="check that every configured root is mounted and accessible",
        )
        return
    placement_names = {placement.variable for placement, _ in validation.placements}
    root_findings = {
        variable: tuple(
            finding
            for finding in validation.report.findings
            if finding.name in {variable, f"{variable}.storage"}
        )
        for variable in placement_names
    }
    unmatched = tuple(
        finding
        for finding in validation.report.findings
        if finding.name.removesuffix(".storage") not in placement_names
    )
    report.extend(unmatched)
    for placement, evidence in validation.placements:
        rotational = "unknown" if evidence.rotational is None else str(evidence.rotational).lower()
        findings = root_findings[placement.variable]
        status = _aggregate_status(findings)
        assessment = "; ".join(item.detail for item in findings)
        report.add(
            f"path.{placement.variable}",
            status,
            (
                f"path={evidence.path}; class={placement.storage_class}; "
                f"filesystem={evidence.filesystem}; device={evidence.device_id}; "
                f"rotational={rotational}; free_bytes={evidence.free_bytes}; "
                f"assessment={assessment}"
            ),
            action=(
                None
                if status == "ready"
                else f"change {placement.variable} in .env, then rerun make readiness"
            ),
        )


def _destination_refusal(config: RuntimeConfig, destination: Path) -> str | None:
    """Return why a resolved report destination is unsafe, or None when it is allowed."""
    results = config.results_dir.resolve()
    if results == Path(results.anchor):
        return "RESULTS_DIR may not be a filesystem root"
    if not contains(results, destination):
        return "JSON report destination must stay inside RESULTS_DIR"
    roots = report_protected_roots(config)
    violation = containment_violation(destination, roots) or containment_violation(results, roots)
    if violation is not None:
        return f"JSON report destination overlaps {violation.detail} ({violation.variable})"
    ancestor = existing_ancestor(destination.parent)
    if not os.access(ancestor, os.W_OK | os.X_OK):
        return "JSON report destination is not writable"
    if destination.exists() and not destination.is_file():
        return "JSON report destination is not a regular file"
    return None


def _blocked_report(report: PreflightReport, detail: str) -> None:
    report.add(
        "report.json",
        "blocked",
        detail,
        action="set RESULTS_DIR or --json-report to a safe writable location",
    )


def _persist_report(
    report: PreflightReport, config: RuntimeConfig, destination: Path
) -> Path | None:
    resolved = destination.expanduser()
    if not resolved.is_absolute():
        resolved = config.project_root / resolved
    resolved = resolved.resolve()
    refusal = _destination_refusal(config, resolved)
    if refusal is not None:
        _blocked_report(report, refusal)
        return None
    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        final = resolved.parent.resolve() / resolved.name
        revalidation = _destination_refusal(config, final)
        if revalidation is not None:
            _blocked_report(report, revalidation)
            return None
        report.write_json(final)
    except OSError as error:
        report.add(
            "report.json",
            "blocked",
            f"JSON report could not be written: {error.__class__.__name__}",
            action="check RESULTS_DIR permissions and free space",
        )
        return None
    return final


def _aggregate_status(findings: tuple[PreflightFinding, ...]) -> CheckStatus:
    statuses = {finding.status for finding in findings}
    if "blocked" in statuses:
        return "blocked"
    if "degraded" in statuses:
        return "degraded"
    return "ready"

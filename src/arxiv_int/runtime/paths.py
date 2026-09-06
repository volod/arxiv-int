"""Safe runtime path resolution, inspection, and layout creation."""

import os
from collections.abc import Callable
from pathlib import Path

from arxiv_int.readiness.report import CheckStatus, PreflightReport
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.containment import overlaps
from arxiv_int.runtime.filesystem import (
    DATABASE_FILESYSTEMS,
    FilesystemEvidence,
    existing_ancestor,
    inspect_filesystem,
)
from arxiv_int.runtime.path_model import PathValidation, RootPlacement, runtime_placements

_RESULTS_CHILDREN = ("normalized", "quarantine", "proofs", "exports")
_DERIVED_VARIABLES = {
    "RUNS_DIR",
    "SERVICE_STATE_DIR",
    "MODEL_CACHE_DIR",
    "TMP_DIR",
}


def _check_targets(
    config: RuntimeConfig, placements: tuple[RootPlacement, ...], report: PreflightReport
) -> None:
    for placement in placements:
        if placement.path == Path(placement.path.anchor):
            report.add(
                placement.variable,
                "blocked",
                f"{placement.variable} may not target a filesystem root",
            )
        if placement.output and overlaps(placement.path, config.project_root):
            report.add(
                placement.variable,
                "blocked",
                f"change {placement.variable}; output overlaps the checkout",
            )


def _report_pairwise_overlaps(
    group: list[RootPlacement], report: PreflightReport, remedy: str
) -> None:
    for index, left in enumerate(group):
        for right in group[index + 1 :]:
            if overlaps(left.path, right.path):
                report.add(
                    left.variable,
                    "blocked",
                    f"{left.variable} overlaps {right.variable}; {remedy}",
                )


def _check_independent_roots(
    placements: tuple[RootPlacement, ...], report: PreflightReport
) -> None:
    primary = [
        placement
        for placement in placements
        if placement.variable not in _DERIVED_VARIABLES | {"PROOF_ARCHIVE_DIR"}
    ]
    _report_pairwise_overlaps(primary, report, "change one root")


def _check_derived_aliasing(placements: tuple[RootPlacement, ...], report: PreflightReport) -> None:
    """Refuse two derived roots that alias one tree, which a reset would erase together."""
    derived = [item for item in placements if item.variable in _DERIVED_VARIABLES]
    _report_pairwise_overlaps(derived, report, "change one derived root")


def _check_proof_overlap(placements: tuple[RootPlacement, ...], report: PreflightReport) -> None:
    proof = next((item for item in placements if item.variable == "PROOF_ARCHIVE_DIR"), None)
    if proof is None:
        return
    for output in (item for item in placements if item.output):
        if overlaps(output.path, proof.path):
            report.add(
                output.variable,
                "blocked",
                f"{output.variable} overlaps PROOF_ARCHIVE_DIR; change {output.variable}",
            )


def _check_derived_roots(
    config: RuntimeConfig, placements: tuple[RootPlacement, ...], report: PreflightReport
) -> None:
    primary = [item for item in placements if item.variable not in _DERIVED_VARIABLES]
    derived = [item for item in placements if item.variable in _DERIVED_VARIABLES]
    for output in derived:
        if output.path == config.results_dir:
            report.add(
                output.variable,
                "blocked",
                f"change {output.variable}; it may not equal RESULTS_DIR",
            )
        for root in primary:
            if root.variable in {"RESULTS_DIR", "PROOF_ARCHIVE_DIR"}:
                continue
            if overlaps(output.path, root.path):
                report.add(
                    output.variable,
                    "blocked",
                    f"{output.variable} overlaps {root.variable}; change {output.variable}",
                )


def _check_dangerous_and_overlapping(
    config: RuntimeConfig, placements: tuple[RootPlacement, ...], report: PreflightReport
) -> None:
    _check_targets(config, placements, report)
    _check_independent_roots(placements, report)
    _check_proof_overlap(placements, report)
    _check_derived_roots(config, placements, report)
    _check_derived_aliasing(placements, report)


def _output_permission_finding(
    placement: RootPlacement, evidence: FilesystemEvidence
) -> tuple[CheckStatus, str] | None:
    path = placement.path
    ancestor = existing_ancestor(path)
    if path.exists() and not path.is_dir():
        return "blocked", f"{placement.variable} is not a directory"
    mode = ancestor.stat().st_mode
    if evidence.read_only or not mode & 0o222 or not os.access(ancestor, os.W_OK | os.X_OK):
        return (
            "blocked",
            f"{placement.variable} is not writable; change {placement.variable} or its permissions",
        )
    if placement.storage_class == "database" and path.exists() and mode & 0o022:
        return "blocked", f"{placement.variable} does not have exclusive write ownership"
    if evidence.free_bytes <= 0:
        return "blocked", f"{placement.variable} has no free space; change {placement.variable}"
    return None


def _source_permission_finding(
    placement: RootPlacement,
) -> tuple[CheckStatus, str] | None:
    path = placement.path
    if not path.is_dir() or not os.access(path, os.R_OK | os.X_OK):
        return "blocked", f"{placement.variable} must be a readable directory"
    return None


def _permission_finding(
    placement: RootPlacement, evidence: FilesystemEvidence
) -> tuple[CheckStatus, str] | None:
    if placement.output:
        return _output_permission_finding(placement, evidence)
    return _source_permission_finding(placement)


def _storage_finding(
    placement: RootPlacement, evidence: FilesystemEvidence
) -> tuple[CheckStatus, str]:
    variable = placement.variable
    if placement.storage_class == "database" and (
        not evidence.ownership_capable or evidence.filesystem not in DATABASE_FILESYSTEMS
    ):
        return (
            "blocked",
            f"{variable} is not on an ownership-capable PostgreSQL filesystem; change {variable}",
        )
    if placement.storage_class == "service-state" and not evidence.ownership_capable:
        return "degraded", f"{variable} cannot express real ownership; change {variable}"
    return "ready", f"{variable} satisfies the {placement.storage_class} storage class"


def validate_runtime_paths(
    config: RuntimeConfig,
    *,
    inspector: Callable[[Path], FilesystemEvidence] = inspect_filesystem,
    variables: frozenset[str] | None = None,
) -> PathValidation:
    """Resolve every root and accumulate safety and storage-class findings."""
    report = PreflightReport("runtime paths")
    placements = runtime_placements(config)
    _check_dangerous_and_overlapping(config, placements, report)
    inspected: list[tuple[RootPlacement, FilesystemEvidence]] = []
    for placement in placements:
        if variables is not None and placement.variable not in variables:
            continue
        evidence = inspector(placement.path)
        inspected.append((placement, evidence))
        permission = _permission_finding(placement, evidence)
        if permission is not None:
            report.add(placement.variable, permission[0], permission[1])
        status, detail = _storage_finding(placement, evidence)
        report.add(f"{placement.variable}.storage", status, detail)
    return PathValidation(tuple(inspected), report)


def create_results_layout(
    config: RuntimeConfig, validation: PathValidation, *, variables: frozenset[str] | None = None
) -> tuple[Path, ...]:
    """Create only the documented output skeleton after all path checks pass."""
    validation.report.require_ready()
    directories = [config.results_dir / name for name in _RESULTS_CHILDREN]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    for placement in runtime_placements(config):
        if not placement.output or placement.variable == "RESULTS_DIR":
            continue
        if variables is not None and placement.variable not in variables:
            continue
        mode = 0o700 if placement.storage_class == "database" else 0o777
        placement.path.mkdir(mode=mode, parents=True, exist_ok=True)
        directories.append(placement.path)
    return tuple(directories)

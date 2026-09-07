"""Orchestrate evolution policy checks against reviewed baselines and migrations."""

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arxiv_int.contracts.evolution.avro_compat import generated_avro_self_compatibility
from arxiv_int.contracts.evolution.baseline import (
    baseline_path,
    build_reviewed_snapshot,
    evolution_root,
    load_baseline,
)
from arxiv_int.contracts.evolution.core import CHANGE_IDENTICAL, version_policy_errors
from arxiv_int.contracts.evolution.migrations import (
    migration_policy_findings,
)
from arxiv_int.contracts.evolution.policy import classify_contract_evolution
from arxiv_int.contracts.generate.pipeline import BASELINE_DDL_RELATIVE
from arxiv_int.contracts.generate.sql_validate import apply_baseline_on_disposable_postgres
from arxiv_int.contracts.registry import FileRegistry

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True)
class EvolutionCheckReport:
    """Aggregated evolution policy findings."""

    findings: tuple[str, ...]
    checked_contracts: int

    @property
    def ok(self) -> bool:
        return not self.findings


def _contract_findings(registry: FileRegistry, contract_id: str) -> list[str]:
    path = baseline_path(registry.root, contract_id)
    if not path.is_file():
        return [f"{contract_id}: missing reviewed baseline at {path}"]
    baseline = load_baseline(path)
    current = build_reviewed_snapshot(registry, contract_id)
    report = classify_contract_evolution(
        baseline_fields=baseline.get("fields") or {},
        current_fields=current.get("fields") or {},
        baseline_projections=baseline.get("projections") or {},
        current_projections=current.get("projections") or {},
        baseline_semantic_hash=(baseline.get("fingerprints") or {}).get("semanticMetadataHash"),
        current_semantic_hash=(current.get("fingerprints") or {}).get("semanticMetadataHash"),
    )
    findings: list[str] = []
    if report.change_class != CHANGE_IDENTICAL:
        findings.append(
            f"{contract_id}: {report.change_class} vs reviewed baseline: "
            + "; ".join(report.details)
        )
        findings.extend(
            version_policy_errors(
                contract_id,
                str(baseline.get("version") or "0.0.0"),
                str(current.get("version") or "0.0.0"),
                report,
            )
        )
    avro_path = registry.root / "generated" / "avro" / f"{contract_id}.avsc"
    if avro_path.is_file():
        findings.extend(
            f"{contract_id}: {item}" for item in generated_avro_self_compatibility(avro_path)
        )
    return findings


def check_evolution_policy(
    contracts_root: Path,
    *,
    project_root: Path | None = None,
    include_migrations: bool = True,
    include_live_sql: bool = True,
) -> EvolutionCheckReport:
    """Check reviewed baselines, Avro self-compat, migrations, and disposable SQL apply."""
    registry = FileRegistry(contracts_root)
    findings: list[str] = []
    if not evolution_root(contracts_root).is_dir():
        findings.append("contracts/evolution directory is missing")
    for contract_id in registry.contract_ids():
        findings.extend(_contract_findings(registry, contract_id))
    root = project_root or contracts_root.parent
    if include_migrations:
        findings.extend(migration_policy_findings(root, contracts_root))
    if include_live_sql:
        baseline = contracts_root / "generated" / BASELINE_DDL_RELATIVE
        if baseline.is_file():
            _LOG.info("applying generated baseline DDL on a disposable database")
            findings.extend(
                apply_baseline_on_disposable_postgres(baseline.read_text(encoding="utf-8"))
            )
    return EvolutionCheckReport(tuple(findings), len(registry.contract_ids()))


def compare_fixture_pair(
    baseline_snapshot: dict[str, Any],
    current_snapshot: dict[str, Any],
) -> tuple[str, tuple[str, ...]]:
    """Classify a fixture baseline/current snapshot pair for tests."""
    report = classify_contract_evolution(
        baseline_fields=baseline_snapshot.get("fields") or {},
        current_fields=current_snapshot.get("fields") or {},
        baseline_projections=baseline_snapshot.get("projections") or {},
        current_projections=current_snapshot.get("projections") or {},
        baseline_semantic_hash=(baseline_snapshot.get("fingerprints") or {}).get(
            "semanticMetadataHash"
        ),
        current_semantic_hash=(current_snapshot.get("fingerprints") or {}).get(
            "semanticMetadataHash"
        ),
    )
    return report.change_class, report.details


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object fixture."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"fixture is not an object: {path}")
    return payload

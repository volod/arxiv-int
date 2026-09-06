"""Aggregate the offline migration checks kept separate from any apply step."""

from dataclasses import dataclass
from pathlib import Path

from arxiv_int.contracts.migrations.authoring import head_revision, read_manifest
from arxiv_int.contracts.migrations.graph import (
    graph_findings,
    head_state_findings,
    manifest_findings,
)
from arxiv_int.contracts.migrations.paths import head_state_path
from arxiv_int.contracts.migrations.render import review_notes
from arxiv_int.contracts.migrations.state import contract_state, diff_states, load_state
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root


@dataclass(frozen=True)
class MigrationCheckReport:
    """Offline migration status without any claim about a live database."""

    findings: tuple[str, ...]
    pending_operations: tuple[str, ...]
    head: str | None
    live_evidence: str = "not-run"

    @property
    def ok(self) -> bool:
        """Return whether every offline gate passed."""
        return not self.findings


def check_migrations(project_root: Path, contracts_root: Path) -> MigrationCheckReport:
    """Check the revision graph, checksums, and contract-to-history drift offline."""
    findings = manifest_findings(project_root)
    findings.extend(graph_findings(project_root))
    findings.extend(head_state_findings(project_root))
    model = load_schema_model_from_root(contracts_root)
    operations = diff_states(load_state(head_state_path(project_root)), contract_state(model))
    pending = tuple(
        f"{operation.kind} {operation.qualified_name}"
        + (f".{operation.column}" if operation.column else "")
        for operation in operations
    )
    if pending:
        findings.append(
            "contract metadata has no matching revision; run 'arxiv-int migrations revision': "
            + "; ".join(pending)
        )
        findings.extend(review_notes(operations))
    return MigrationCheckReport(
        findings=tuple(findings),
        pending_operations=pending,
        head=head_revision(read_manifest(project_root)),
    )

"""Refusal-first adoption of an existing database."""

from pathlib import Path

from arxiv_int.contracts.migrations.errors import UnsafeAdoptionError
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel


def adoption_findings(
    project_root: Path,
    model: ContractSchemaModel,
    *,
    catalog_findings: list[str] | None = None,
) -> list[str]:
    """Return every reason an existing database may not be stamped at a baseline."""
    del project_root, model
    if catalog_findings is None:
        return ["live catalog equivalence was not established; adoption stays refused (not-run)"]
    return list(catalog_findings)


def require_safe_adoption(
    project_root: Path,
    model: ContractSchemaModel,
    *,
    catalog_findings: list[str] | None = None,
) -> None:
    """Raise unless a database is proved equivalent to the contract baseline."""
    findings = adoption_findings(project_root, model, catalog_findings=catalog_findings)
    if findings:
        raise UnsafeAdoptionError(
            "refusing to stamp an unverified database; repair these first: " + "; ".join(findings)
        )

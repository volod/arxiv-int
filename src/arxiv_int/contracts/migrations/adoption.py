"""Legacy SQL inventory and refusal-first adoption of an existing database."""

import re
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.contracts.migrations.errors import UnsafeAdoptionError
from arxiv_int.contracts.migrations.paths import legacy_migrations_dir, legacy_schema_sql
from arxiv_int.contracts.sqlalchemy.model import ContractSchemaModel

_CREATE_TABLE = re.compile(
    r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?P<name>[a-zA-Z0-9_.\"]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class LegacyInventory:
    """Legacy adoption evidence retained beside the owned revision history."""

    files: tuple[Path, ...]
    declared_tables: tuple[str, ...]
    schema_export: Path | None

    @property
    def present(self) -> bool:
        """Return whether any legacy evidence exists."""
        return bool(self.files) or self.schema_export is not None


def _tables_in(text: str) -> list[str]:
    return [match.group("name").replace('"', "") for match in _CREATE_TABLE.finditer(text)]


def inventory_legacy_sql(project_root: Path) -> LegacyInventory:
    """Inventory retained dbmate-shaped SQL without treating it as an execution engine."""
    directory = legacy_migrations_dir(project_root)
    files = tuple(sorted(directory.glob("*.sql"))) if directory.is_dir() else ()
    declared: list[str] = []
    for path in files:
        declared.extend(_tables_in(path.read_text(encoding="utf-8")))
    export = legacy_schema_sql(project_root)
    return LegacyInventory(
        files=files,
        declared_tables=tuple(sorted(set(declared))),
        schema_export=export if export.is_file() else None,
    )


def legacy_binding_findings(inventory: LegacyInventory, model: ContractSchemaModel) -> list[str]:
    """Map every legacy table name to a contract binding, refusing ambiguity."""
    owned = {table.qualified_name for table in model.tables}
    by_bare: dict[str, list[str]] = {}
    for name in owned:
        by_bare.setdefault(name.split(".")[-1], []).append(name)
    findings: list[str] = []
    for declared in inventory.declared_tables:
        if "." in declared:
            if declared not in owned:
                findings.append(f"legacy table '{declared}' has no contract binding")
            continue
        candidates = sorted(by_bare.get(declared, ()))
        if not candidates:
            findings.append(f"legacy table '{declared}' has no contract binding")
        elif len(candidates) > 1:
            findings.append(
                f"legacy unqualified table '{declared}' is ambiguous between "
                f"{', '.join(candidates)}; declare the schema before adoption"
            )
    return findings


def adoption_findings(
    project_root: Path,
    model: ContractSchemaModel,
    *,
    catalog_findings: list[str] | None = None,
) -> list[str]:
    """Return every reason an existing database may not be stamped at a baseline."""
    inventory = inventory_legacy_sql(project_root)
    findings = legacy_binding_findings(inventory, model)
    if catalog_findings is None:
        findings.append(
            "live catalog equivalence was not established; adoption stays refused (not-run)"
        )
    else:
        findings.extend(catalog_findings)
    return findings


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

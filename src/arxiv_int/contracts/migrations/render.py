"""Render immutable Alembic Python revision modules for review."""

from typing import Any

from arxiv_int.contracts.migrations.operations import (
    downgrade_lines,
    literal,
    upgrade_lines,
)
from arxiv_int.contracts.migrations.state import (
    OP_ALTER_COLUMN,
    OP_DROP_COLUMN,
    OP_DROP_TABLE,
    SchemaOperation,
)

_TEMPLATE = '''"""{message}

Generated from contract-derived SQLAlchemy metadata. Definitions below are frozen:
this revision never imports today's contracts to decide what it creates.

Revision ID: {revision}
Revises: {down_revision}
Contract fingerprints: see CONTRACT_FINGERPRINTS.
"""

{imports}

revision: str = "{revision}"
down_revision: str | None = {down_revision_literal}
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {fingerprints}
REVIEW_NOTES: tuple[str, ...] = {review_notes}
IRREVERSIBLE_REASON: str = {irreversible_reason}


def upgrade() -> None:
    """Apply the frozen operations reviewed with this revision."""
{upgrade_body}


def downgrade() -> None:
    """Reverse the frozen operations, or refuse when data cannot be restored."""
{downgrade_body}
'''


def _mappingliteral(values: dict[str, str]) -> str:
    if not values:
        return "{}"
    items = ",\n".join(
        f"    {literal(key)}: {literal(value)}" for key, value in sorted(values.items())
    )
    return "{\n" + items + ",\n}"


def _tupleliteral(values: tuple[str, ...]) -> str:
    if not values:
        return "()"
    return "(\n" + "".join(f"    {literal(item)},\n" for item in values) + ")"


def review_notes(operations: tuple[SchemaOperation, ...]) -> tuple[str, ...]:
    """Return the reviewed-handling notes autogeneration cannot decide on its own."""
    notes: list[str] = []
    for operation in operations:
        if operation.kind == OP_DROP_TABLE:
            notes.append(
                f"confirm '{operation.qualified_name}' is a removal and not a rename; "
                "an approved plan, backup, free-space check and rollback path are required"
            )
        elif operation.kind == OP_DROP_COLUMN:
            notes.append(
                f"confirm '{operation.qualified_name}.{operation.column}' is a removal and not a "
                "rename; an approved plan, backup and rollback path are required"
            )
        elif operation.kind == OP_ALTER_COLUMN:
            notes.append(
                f"review '{operation.qualified_name}.{operation.column}' for narrowing, rewrite "
                "cost and any required data backfill before applying"
            )
    return tuple(notes)


def _import_block(upgrade_body: str, downgrade_body: str) -> str:
    """Import only what the frozen operations use, so revisions stay lint-clean."""
    body = f"{upgrade_body}\n{downgrade_body}"
    third_party = ["from alembic import op"]
    if "sa." in body:
        third_party.insert(0, "import sqlalchemy as sa")
    if "postgresql." in body:
        third_party.append("from sqlalchemy.dialects import postgresql")
    lines = list(third_party)
    if "IrreversibleRevisionError" in body:
        lines.extend(
            ["", "from arxiv_int.contracts.migrations.errors import IrreversibleRevisionError"]
        )
    return "\n".join(lines)


def render_revision(
    *,
    revision: str,
    down_revision: str | None,
    message: str,
    operations: tuple[SchemaOperation, ...],
    before: dict[str, Any],
    after: dict[str, Any],
    fingerprints: dict[str, str],
) -> str:
    """Render one immutable revision module for review."""
    upgrade_body = "\n".join(upgrade_lines(operations, after))
    downgrade_body = "\n".join(downgrade_lines(operations, before))
    irreversible = any(operation.data_losing for operation in operations)
    reason = (
        "this revision removes owned objects; restore from the approved backup instead "
        "of downgrading"
        if irreversible
        else ""
    )
    body = _TEMPLATE.format(
        imports=_import_block(upgrade_body, downgrade_body),
        message=message,
        revision=revision,
        down_revision=down_revision or "base",
        down_revision_literal=literal(down_revision),
        fingerprints=_mappingliteral(fingerprints),
        review_notes=_tupleliteral(review_notes(operations)),
        irreversible_reason=literal(reason) if reason else '""',
        upgrade_body=upgrade_body,
        downgrade_body=downgrade_body,
    )
    return body

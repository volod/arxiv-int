"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
"""

import sqlalchemy as sa
from alembic import op

from arxiv_int.contracts.migrations.errors import IrreversibleRevisionError

revision: str = ${repr(up_revision)}
down_revision: str | None = ${repr(down_revision)}
branch_labels: None = None
depends_on: None = None

CONTRACT_FINGERPRINTS: dict[str, str] = {}
REVIEW_NOTES: tuple[str, ...] = ()
IRREVERSIBLE_REASON: str = ""


def upgrade() -> None:
    """Apply the frozen operations reviewed with this revision."""
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    """Reverse the frozen operations, or refuse when data cannot be restored."""
    ${downgrades if downgrades else "pass"}

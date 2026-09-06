"""Contract-derived Alembic revision authoring, checks, and apply wrappers."""

from arxiv_int.contracts.migrations.adoption import (
    LegacyInventory,
    adoption_findings,
    inventory_legacy_sql,
    require_safe_adoption,
)
from arxiv_int.contracts.migrations.authoring import RevisionCandidate, generate_revision
from arxiv_int.contracts.migrations.check import MigrationCheckReport, check_migrations
from arxiv_int.contracts.migrations.errors import (
    IrreversibleRevisionError,
    MigrationRunnerUnavailableError,
    UnsafeAdoptionError,
)
from arxiv_int.contracts.migrations.runner import (
    DATABASE_URL_VARIABLE,
    STATUS_FAILED,
    STATUS_NOT_RUN,
    STATUS_OK,
    RunnerOutcome,
    current_revision,
    downgrade,
    redact_url,
    runner_available,
    upgrade,
)
from arxiv_int.contracts.migrations.state import SchemaOperation, contract_state, diff_states

__all__ = [
    "DATABASE_URL_VARIABLE",
    "STATUS_FAILED",
    "STATUS_NOT_RUN",
    "STATUS_OK",
    "IrreversibleRevisionError",
    "LegacyInventory",
    "MigrationCheckReport",
    "MigrationRunnerUnavailableError",
    "RevisionCandidate",
    "RunnerOutcome",
    "SchemaOperation",
    "UnsafeAdoptionError",
    "adoption_findings",
    "check_migrations",
    "contract_state",
    "current_revision",
    "diff_states",
    "downgrade",
    "generate_revision",
    "inventory_legacy_sql",
    "redact_url",
    "require_safe_adoption",
    "runner_available",
    "upgrade",
]

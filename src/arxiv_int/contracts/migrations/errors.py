"""Explicit migration failures shared by revisions and wrappers."""


class IrreversibleRevisionError(RuntimeError):
    """Raised when a revision cannot be downgraded without data recovery."""


class MigrationRunnerUnavailableError(RuntimeError):
    """Raised when Alembic or a required live database is unavailable."""


class UnsafeAdoptionError(RuntimeError):
    """Raised when an existing database cannot be proved equivalent to a baseline."""

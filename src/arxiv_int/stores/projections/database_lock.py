"""Serialize projection publication and cleanup across all local tool roots."""

from sqlalchemy import Connection, text

from arxiv_int.stores.projections.ids import projection_id
from arxiv_int.stores.projections.registry import ActivationRefusedError, active_projection_id

# One PostgreSQL advisory-lock namespace for the projection catalog.
PROJECTION_LOCK_KEY = 1095915600


def lock_projection_catalog(connection: Connection) -> None:
    """Fail promptly when another transaction owns projection publication or cleanup."""
    held = connection.execute(
        text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": PROJECTION_LOCK_KEY}
    ).scalar()
    if not held:
        raise ActivationRefusedError("projection catalog is already owned by another operation")


def refuse_active_version(connection: Connection, kinds: tuple[str, ...], version: str) -> None:
    """Never rebuild engine objects referenced by active pointers, including AGE autocommit."""
    for kind in kinds:
        if active_projection_id(connection, kind) == projection_id(kind, version):
            raise ActivationRefusedError("active projection version is immutable; use a new run id")

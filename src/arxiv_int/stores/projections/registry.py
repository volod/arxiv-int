"""Typed SQLAlchemy operations for projection metadata and active pointers."""

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, select
from sqlalchemy.dialects.postgresql import insert

from arxiv_int.stores.projections.ids import evidence_id, require_ident
from arxiv_int.stores.projections.model import (
    STATUS_ACTIVE,
    STATUS_DROPPED,
    STATUS_FAILED,
    STATUS_RETIRED,
    STATUS_STAGING,
    STATUS_VALIDATED,
)
from arxiv_int.stores.projections.tables import ACTIVE, CLEANUP, EVIDENCE, PROJECTIONS

__all__ = [
    "ACTIVE",
    "CLEANUP",
    "EVIDENCE",
    "PROJECTIONS",
    "ActivationRefusedError",
    "active_projection_id",
    "cleanup_candidates",
    "mark_dropped",
    "mark_failed",
    "record_validation",
    "switch_active",
    "upsert_staging",
    "validated_status",
    "write_evidence_rows",
]


class ActivationRefusedError(RuntimeError):
    """Raised when a failed or incomplete projection tries to become active."""


def _now() -> datetime:
    return datetime.now(UTC)


def upsert_staging(
    connection: Connection,
    *,
    projection_id: str,
    kind: str,
    version_id: str,
    engine: str,
    engine_object: str,
    run_id: str,
    schema_version: str,
) -> None:
    """Insert or reset one staging projection row without touching the active pointer."""
    require_ident(kind)
    require_ident(version_id)
    statement = insert(PROJECTIONS).values(
        projection_id=projection_id,
        kind=kind,
        version_id=version_id,
        status=STATUS_STAGING,
        schema_version=schema_version,
        engine=engine,
        engine_object=engine_object,
        run_id=run_id,
        created_at=_now(),
    )
    assigned = {
        "status": STATUS_STAGING,
        "engine": engine,
        "engine_object": engine_object,
        "run_id": run_id,
        "quality_status": None,
        "checksum": None,
        "row_count": None,
    }
    statement = statement.on_conflict_do_update(index_elements=["projection_id"], set_=assigned)
    connection.execute(statement)


def record_validation(
    connection: Connection,
    *,
    projection_id: str,
    status: str,
    row_count: int,
    checksum: str,
    quality_status: str,
    input_fingerprint: str,
    last_committed_id: str | None = None,
) -> None:
    """Write validation fields after quality runs and before any pointer switch."""
    connection.execute(
        PROJECTIONS.update()
        .where(PROJECTIONS.c.projection_id == projection_id)
        .values(
            status=status,
            row_count=row_count,
            checksum=checksum,
            quality_status=quality_status,
            input_fingerprint=input_fingerprint,
            last_committed_id=last_committed_id,
        )
    )


def write_evidence_rows(
    connection: Connection, projection_id: str, checks: Sequence[Mapping[str, Any]]
) -> None:
    """Replace retained check evidence for one projection version."""
    connection.execute(EVIDENCE.delete().where(EVIDENCE.c.projection_id == projection_id))
    for item in checks:
        name = str(item["check_name"])
        connection.execute(
            insert(EVIDENCE).values(
                evidence_id=evidence_id(projection_id, name),
                projection_id=projection_id,
                check_name=name,
                status=str(item["status"]),
                detail=item.get("detail"),
                checked_count=int(item.get("checked_count") or 0),
                failed_count=int(item.get("failed_count") or 0),
                created_at=_now(),
            )
        )


def active_projection_id(connection: Connection, kind: str) -> str | None:
    """Return the active projection id for one kind, if any."""
    row = connection.execute(select(ACTIVE.c.projection_id).where(ACTIVE.c.kind == kind)).first()
    return None if row is None else str(row[0])


def switch_active(
    connection: Connection, *, kind: str, projection_id: str, publishable: bool
) -> None:
    """Atomically point ``kind`` at a validated projection, or refuse."""
    if not publishable:
        raise ActivationRefusedError(
            f"refusing to activate {projection_id}: quality results are not publishable"
        )
    current = active_projection_id(connection, kind)
    if current == projection_id:
        return
    if current is not None:
        connection.execute(
            PROJECTIONS.update()
            .where(PROJECTIONS.c.projection_id == current)
            .values(status=STATUS_RETIRED)
        )
    connection.execute(
        PROJECTIONS.update()
        .where(PROJECTIONS.c.projection_id == projection_id)
        .values(status=STATUS_ACTIVE)
    )
    statement = insert(ACTIVE).values(
        kind=kind,
        projection_id=projection_id,
        previous_projection_id=current,
        switched_at=_now(),
    )
    statement = statement.on_conflict_do_update(
        index_elements=["kind"],
        set_={
            "projection_id": projection_id,
            "previous_projection_id": current,
            "switched_at": _now(),
        },
    )
    connection.execute(statement)


def mark_failed(connection: Connection, projection_id: str, quality_status: str) -> None:
    """Mark a staging build failed without changing the active pointer."""
    connection.execute(
        PROJECTIONS.update()
        .where(PROJECTIONS.c.projection_id == projection_id)
        .values(status=STATUS_FAILED, quality_status=quality_status)
    )


def cleanup_candidates(connection: Connection) -> tuple[dict[str, str], ...]:
    """Return failed or retired projections that are not currently active."""
    active_ids = {str(row[0]) for row in connection.execute(select(ACTIVE.c.projection_id))}
    rows = connection.execute(
        select(
            PROJECTIONS.c.projection_id,
            PROJECTIONS.c.kind,
            PROJECTIONS.c.engine_object,
            PROJECTIONS.c.status,
        ).where(PROJECTIONS.c.status.in_((STATUS_FAILED, STATUS_RETIRED)))
    ).fetchall()
    planned: list[dict[str, str]] = []
    for row in rows:
        if str(row[0]) in active_ids:
            continue
        planned.append(
            {
                "projection_id": str(row[0]),
                "kind": str(row[1]),
                "engine_object": str(row[2] or ""),
                "status": str(row[3]),
            }
        )
    return tuple(planned)


def mark_dropped(connection: Connection, projection_id: str) -> None:
    """Record that engine objects for a retired or failed version were dropped."""
    connection.execute(
        PROJECTIONS.update()
        .where(PROJECTIONS.c.projection_id == projection_id)
        .values(status=STATUS_DROPPED)
    )


def validated_status(publishable: bool) -> str:
    """Return validated or failed from a shared quality publication decision."""
    return STATUS_VALIDATED if publishable else STATUS_FAILED

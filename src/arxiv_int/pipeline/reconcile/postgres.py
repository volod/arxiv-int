"""Typed SQLAlchemy transactions for tombstones, pins, and prune events."""

from collections.abc import Sequence
from uuid import uuid4

from sqlalchemy import Engine, insert, select
from sqlalchemy.engine import Connection

from arxiv_int.pipeline.reconcile.model import Tombstone
from arxiv_int.pipeline.reconcile.tables import ARTIFACT_PIN, PRUNE_EVENT, SOURCE_TOMBSTONE


def insert_tombstones(connection: Connection, rows: Sequence[Tombstone]) -> tuple[str, ...]:
    """Insert source tombstones; archive bytes are never deleted here."""
    ids: list[str] = []
    for row in rows:
        tombstone_id = uuid4().hex
        connection.execute(
            insert(SOURCE_TOMBSTONE).values(
                tombstone_id=tombstone_id,
                occurrence_id=row.occurrence_id,
                silo_id=row.silo_id,
                relative_path=row.relative_path,
                content_hash=row.content_hash,
                scan_id=row.scan_id,
                generation_id=row.generation_id,
                last_occurrence=row.last_occurrence,
                reason=row.reason,
            )
        )
        ids.append(tombstone_id)
    return tuple(ids)


def insert_prune_event(
    connection: Connection,
    *,
    plan_id: str,
    fingerprint: str,
    status: str,
    bytes_removed: int,
    detail: str = "",
) -> str:
    """Record a planned, applied, or refused prune."""
    event_id = uuid4().hex
    connection.execute(
        insert(PRUNE_EVENT).values(
            event_id=event_id,
            plan_id=plan_id,
            fingerprint=fingerprint,
            status=status,
            bytes_removed=bytes_removed,
            detail=detail,
        )
    )
    return event_id


def insert_pin(
    connection: Connection,
    *,
    directory: str,
    reuse_key: str,
    kind: str,
    generation_id: str,
) -> str:
    """Pin a derived attempt so prune must refuse it."""
    pin_id = uuid4().hex
    connection.execute(
        insert(ARTIFACT_PIN).values(
            pin_id=pin_id,
            directory=directory,
            reuse_key=reuse_key,
            kind=kind,
            generation_id=generation_id,
        )
    )
    return pin_id


def load_tombstones(connection: Connection, generation_id: str) -> tuple[str, ...]:
    """Return occurrence ids tombstoned for one generation."""
    rows = connection.execute(
        select(SOURCE_TOMBSTONE.c.occurrence_id).where(
            SOURCE_TOMBSTONE.c.generation_id == generation_id
        )
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def insert_tombstones_with_engine(engine: Engine, rows: Sequence[Tombstone]) -> tuple[str, ...]:
    """Open one transaction and insert tombstones."""
    with engine.begin() as connection:
        return insert_tombstones(connection, rows)

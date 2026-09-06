"""Row-count, checksum, and sampled-path reconciliation against relational inputs."""

from collections.abc import Sequence
from typing import Any

from sqlalchemy import Connection, text

from arxiv_int.stores.projections.ids import logical_checksum, require_ident
from arxiv_int.stores.projections.model import DEFAULT_SAMPLE_LIMIT, DEFAULT_WALK_DEPTH


def fetch_ids(connection: Connection, qualified: str, column: str) -> tuple[str, ...]:
    """Return ordered logical ids from one relation."""
    schema, _, name = qualified.partition(".")
    if not name:
        raise ValueError(f"qualified table required, got {qualified!r}")
    require_ident(schema)
    require_ident(name)
    require_ident(column)
    rows = connection.execute(
        text(f"SELECT {column} FROM {schema}.{name} WHERE {column} IS NOT NULL ORDER BY 1")
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def counts_match(expected: Sequence[str], observed: Sequence[str]) -> bool:
    """Return whether observed ids are a permutation-stable copy of expected ids."""
    return sorted(expected) == sorted(observed) and len(expected) == len(observed)


def checksum_for(ids: Sequence[str]) -> str:
    """Return the logical-id fingerprint used across rebuilds."""
    return logical_checksum(tuple(ids))


def one_hop_sql(
    connection: Connection, edges_table: str, start_id: str, *, depth: int = DEFAULT_WALK_DEPTH
) -> tuple[tuple[str, str], ...]:
    """Walk bounded outgoing edges with recursive SQL as the correctness reference."""
    schema, _, table = edges_table.partition(".")
    require_ident(schema)
    require_ident(table)
    statement = text(
        "WITH RECURSIVE walk AS ("
        "SELECT subject_object_id AS src, object_object_id AS dst, 1 AS depth "
        f"FROM {schema}.{table} WHERE subject_object_id = :start "
        "UNION ALL "
        "SELECT e.subject_object_id, e.object_object_id, w.depth + 1 "
        f"FROM walk w JOIN {schema}.{table} e ON e.subject_object_id = w.dst "
        "WHERE w.depth < :depth"
        ") SELECT src, dst FROM walk ORDER BY 1, 2"
    )
    rows = connection.execute(statement, {"start": start_id, "depth": depth}).fetchall()
    return tuple((str(row[0]), str(row[1])) for row in rows)


def sample_starts(ids: Sequence[str], *, limit: int = DEFAULT_SAMPLE_LIMIT) -> tuple[str, ...]:
    """Select a deterministic sample of vertex ids."""
    ordered = sorted(ids)
    if len(ordered) <= limit:
        return tuple(ordered)
    step = max(1, len(ordered) // limit)
    picked = [ordered[index] for index in range(0, len(ordered), step)]
    return tuple(picked[:limit])


def relation_exists(connection: Connection, qualified: str) -> bool:
    """Return whether a schema-qualified table exists."""
    schema, _, table = qualified.partition(".")
    require_ident(schema)
    require_ident(table)
    exists = connection.execute(
        text(
            "SELECT EXISTS (SELECT 1 FROM pg_tables "
            "WHERE schemaname = :schema AND tablename = :table)"
        ),
        {"schema": schema, "table": table},
    ).scalar()
    return bool(exists)


def fetch_maps(
    connection: Connection, qualified: str, columns: Sequence[str]
) -> tuple[dict[str, Any], ...]:
    """Return row mappings for export and AGE load."""
    schema, _, table = qualified.partition(".")
    require_ident(schema)
    require_ident(table)
    selected = ", ".join(require_ident(name) for name in columns)
    rows = connection.execute(
        text(f"SELECT {selected} FROM {schema}.{table} ORDER BY 1")
    ).mappings()
    return tuple(dict(row) for row in rows)

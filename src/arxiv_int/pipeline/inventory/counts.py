"""Disk aggregates for source bytes, member bytes and exact content duplicates."""

import sqlite3


def inventory_counts(database: sqlite3.Connection, silo: str | None = None) -> dict[str, int]:
    """Never materialize all content hashes in Python to compute coverage or dedupe."""
    where = " WHERE silo=?" if silo is not None else ""
    row = database.execute(
        "SELECT count(*), coalesce(sum(json_extract(payload,'$.size')),0), "
        "sum(json_extract(payload,'$.status')='quarantined'), "
        "count(json_extract(payload,'$.content_hash')) - "
        "count(DISTINCT json_extract(payload,'$.content_hash')), "
        "sum(json_array_length(json_extract(payload,'$.members'))=0), "
        "sum(CASE WHEN json_array_length(json_extract(payload,'$.members'))=0 "
        "THEN json_extract(payload,'$.size') ELSE 0 END), "
        "sum(json_extract(payload,'$.reason') LIKE 'encrypted%'), "
        "sum(json_extract(payload,'$.reason') LIKE 'unsupported%') "
        "FROM observations" + where,
        (silo,) if silo is not None else (),
    ).fetchone()
    names = (
        "occurrences",
        "bytes",
        "quarantined",
        "duplicates",
        "source_entries",
        "source_bytes",
        "encrypted",
        "unsupported",
    )
    return dict(zip(names, (int(value or 0) for value in row), strict=True))

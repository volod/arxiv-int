"""Idempotent import of portable organizer path-event ledgers."""

from pathlib import Path

from arxiv_int.query.evidence.catalog import load_ledger, write_ledger
from arxiv_int.query.evidence.model import ImportReport, PathEvent


def import_ledger(
    source: Path,
    destination: Path,
    *,
    ledger_id: str = "",
) -> ImportReport:
    """Merge source events into the destination ledger without rewriting provenance."""
    incoming_id, incoming = load_ledger(source)
    stored_id, stored = load_ledger(destination)
    existing = {item.event_id: item for item in stored}
    merged: list[PathEvent] = list(stored)
    inserted = 0
    skipped = 0
    refused = 0
    findings: list[str] = []
    seen_incoming: dict[str, PathEvent] = {}
    for event in incoming:
        prior = seen_incoming.get(event.event_id)
        if prior is not None and prior != event:
            refused += 1
            findings.append(f"duplicate incoming event_id {event.event_id}")
            continue
        seen_incoming[event.event_id] = event
        current = existing.get(event.event_id)
        if current is None:
            existing[event.event_id] = event
            merged.append(event)
            inserted += 1
            continue
        if current != event:
            refused += 1
            findings.append(f"conflicting event_id {event.event_id}")
            continue
        skipped += 1
    assigned = ledger_id or incoming_id or stored_id or source.stem
    if inserted or not destination.exists():
        write_ledger(destination, assigned, tuple(merged))
    return ImportReport(
        ledger_id=assigned,
        inserted=inserted,
        skipped=skipped,
        refused=refused,
        findings=tuple(findings),
    )

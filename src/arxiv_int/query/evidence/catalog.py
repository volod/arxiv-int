"""Load and persist sealed evidence catalogs and path-event ledgers."""

import json
from pathlib import Path
from typing import Any

from arxiv_int.query.evidence.codec import (
    catalog_from_payload,
    catalog_payload,
    event_from_payload,
    event_payload,
)
from arxiv_int.query.evidence.model import (
    CATALOG_SCHEMA,
    LEDGER_SCHEMA,
    EvidenceCatalog,
    EvidenceError,
    PathEvent,
)

EVIDENCE_DIR = Path("normalized") / "evidence"
CATALOG_NAME = "catalog.json"
LEDGER_NAME = "path-events.json"


def default_catalog_path(results_dir: Path) -> Path:
    """Return the operator evidence catalog under RESULTS_DIR."""
    return results_dir / EVIDENCE_DIR / CATALOG_NAME


def default_ledger_path(results_dir: Path) -> Path:
    """Return the portable path-event ledger under RESULTS_DIR."""
    return results_dir / EVIDENCE_DIR / LEDGER_NAME


def load_catalog(path: Path) -> EvidenceCatalog:
    """Read one sealed evidence catalog without opening archive files."""
    payload = read_json_object(path)
    schema = str(payload.get("schema", CATALOG_SCHEMA))
    if schema != CATALOG_SCHEMA:
        raise EvidenceError(f"unsupported evidence-catalog schema {schema!r}")
    return catalog_from_payload(payload, schema)


def load_ledger(path: Path) -> tuple[str, tuple[PathEvent, ...]]:
    """Read a portable organizer ledger, or an empty store when the file is absent."""
    if not path.exists():
        return "", ()
    payload = read_json_object(path)
    schema = str(payload.get("schema", LEDGER_SCHEMA))
    if schema != LEDGER_SCHEMA:
        raise EvidenceError(f"unsupported path-event-ledger schema {schema!r}")
    events = tuple(event_from_payload(item) for item in payload.get("events") or ())
    return str(payload.get("ledger_id") or ""), events


def write_ledger(path: Path, ledger_id: str, events: tuple[PathEvent, ...]) -> None:
    """Replace the portable ledger with the merged event set."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "events": [event_payload(item) for item in events],
        "ledger_id": ledger_id,
        "schema": LEDGER_SCHEMA,
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_catalog(path: Path, catalog: EvidenceCatalog) -> None:
    """Write a sealed catalog for fixtures and tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(catalog_payload(catalog), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_json_object(path: Path) -> dict[str, Any]:
    """Read a JSON object from disk."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise EvidenceError(f"cannot read evidence file {path.name}") from error
    if not isinstance(raw, dict):
        raise EvidenceError(f"evidence file {path.name} must be a JSON object")
    return raw

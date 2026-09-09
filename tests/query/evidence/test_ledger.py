"""Portable path-event import is idempotent and refuses conflicting ids."""

from pathlib import Path

from arxiv_int.query.evidence.catalog import load_ledger, write_ledger
from arxiv_int.query.evidence.ledger import import_ledger
from arxiv_int.query.evidence.model import PathEvent
from tests.query.evidence._builders import event, save_ledger, sha256_bytes

_DIGEST = sha256_bytes(b"invoice-bytes")


def _payload(event_id: str, path: str = "docs/invoice.pdf") -> PathEvent:
    return event(event_id, "doc-dup", "alpha", "initial", path, _DIGEST)


def test_repeated_ledger_import_is_idempotent(tmp_path: Path) -> None:
    source = tmp_path / "incoming.json"
    destination = tmp_path / "store.json"
    save_ledger(source, (_payload("ev-1"), _payload("ev-2", "docs/other.pdf")))
    first = import_ledger(source, destination, ledger_id="org-1")
    assert first.inserted == 2
    assert first.skipped == 0
    assert first.refused == 0
    before = destination.read_bytes()
    second = import_ledger(source, destination, ledger_id="org-1")
    assert second.inserted == 0
    assert second.skipped == 2
    assert second.refused == 0
    assert destination.read_bytes() == before
    _ledger_id, stored = load_ledger(destination)
    assert len(stored) == 2


def test_conflicting_event_id_is_refused_without_rewrite(tmp_path: Path) -> None:
    destination = tmp_path / "store.json"
    save_ledger(destination, (_payload("ev-1"),))
    before = destination.read_bytes()
    incoming = tmp_path / "conflict.json"
    other = event(
        "ev-1", "doc-dup", "alpha", "rename", "docs/new.pdf", _DIGEST, previous="docs/invoice.pdf"
    )
    write_ledger(incoming, "org-1", (other,))
    report = import_ledger(incoming, destination)
    assert report.inserted == 0
    assert report.refused == 1
    assert destination.read_bytes() == before

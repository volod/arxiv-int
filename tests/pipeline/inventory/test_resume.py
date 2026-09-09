"""Interruption, permission failures and source mutation rollback."""

from pathlib import Path
from typing import BinaryIO

import pytest

from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.inventory import checkpoint as checkpoint_module
from arxiv_int.pipeline.inventory import read
from arxiv_int.pipeline.inventory.model import InventoryPolicy, Observation
from tests.pipeline.inventory.conftest import run_inventory


def test_interrupt_resumes_completed_files(
    context: StageContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = context.silos[0].root
    for index in range(3):
        (root / str(index)).write_text(f"file {index}")
    original = checkpoint_module.observe
    calls = 0

    def interrupted(*args: object, **kwargs: object):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        yield from original(*args, **kwargs)

    monkeypatch.setattr(checkpoint_module, "observe", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run_inventory(context)
    assert not list(context.results_dir.rglob("inventory.json"))
    monkeypatch.setattr(checkpoint_module, "observe", original)
    summary, rows, _ = run_inventory(context)
    assert len(rows) == 3
    assert summary["resumed_files"] == 1
    summary, again, _ = run_inventory(context)
    assert summary["resumed_files"] == 3
    assert {row["occurrence_id"] for row in again} == {row["occurrence_id"] for row in rows}


def test_permission_failure_is_recorded_and_retried(
    context: StageContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    (context.silos[0].root / "denied").write_text("payload")
    original = read.open_source

    def denied(_root: Path, _relative: str) -> int:
        raise PermissionError("fixture")

    monkeypatch.setattr(read, "open_source", denied)
    _, rows, _ = run_inventory(context)
    assert rows[0]["reason"] == "unreadable"
    assert rows[0]["content_hash"] is None
    monkeypatch.setattr(read, "open_source", original)
    summary, rows, _ = run_inventory(context)
    assert summary["resumed_files"] == 0
    assert rows[0]["status"] == "ready"


def test_mutation_discards_all_file_observations(
    context: StageContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = context.silos[0].root / "changing"
    path.write_text("before")
    original = read._hash

    def mutate(handle: BinaryIO, item: Observation, policy: InventoryPolicy) -> Observation:
        result = original(handle, item, policy)
        path.write_text("after!")
        return result

    monkeypatch.setattr(read, "_hash", mutate)
    with pytest.raises(ValueError, match="source set changed"):
        run_inventory(context)
    assert not list(context.results_dir.rglob("inventory.json"))
    import json
    import sqlite3

    with sqlite3.connect(next(context.results_dir.rglob("checkpoint-*.sqlite"))) as database:
        rows = [json.loads(row[0]) for row in database.execute("SELECT payload FROM observations")]
    assert len(rows) == 1
    assert rows[0]["reason"] == "unstable"
    assert rows[0]["content_hash"] is None

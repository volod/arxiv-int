"""The store-wide load lock serializes lexical loads without blocking the build."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from arxiv_int.pipeline.load_lexical import stage as stage_module
from arxiv_int.pipeline.load_lexical.lock import (
    LOAD_LOCK_KEY,
    LexicalLoadBusyError,
    hold_load_lock,
)
from arxiv_int.pipeline.load_lexical.stage import LoadLexicalStage
from arxiv_int.stores.projections.database_lock import PROJECTION_LOCK_KEY

_ACQUIRE = "SELECT pg_try_advisory_lock(:key)"
_RELEASE = "SELECT pg_advisory_unlock(:key)"


def _connection(acquired: bool) -> MagicMock:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = acquired
    return connection


def _statements(connection: MagicMock) -> list[str]:
    return [str(item.args[0]) for item in connection.execute.call_args_list]


def test_load_lock_key_is_distinct_from_the_projection_catalog() -> None:
    assert LOAD_LOCK_KEY != PROJECTION_LOCK_KEY


def test_owned_lock_refuses_before_the_body_runs() -> None:
    connection = _connection(False)
    with (
        pytest.raises(LexicalLoadBusyError, match="another load-lexical run"),
        hold_load_lock(connection),
    ):
        pytest.fail("the body must not run while another load owns the store")
    assert _statements(connection) == [_ACQUIRE]


def test_lock_is_released_after_the_body_fails() -> None:
    connection = _connection(True)
    with pytest.raises(RuntimeError, match="load failed"), hold_load_lock(connection):
        raise RuntimeError("load failed")
    assert _statements(connection) == [_ACQUIRE, _RELEASE]


def _step(events: list[str], name: str, value: Any = None) -> Callable[..., Any]:
    def call(*_args: Any, **_kwargs: Any) -> Any:
        events.append(name)
        return value

    return call


def _stage(monkeypatch: pytest.MonkeyPatch, events: list[str]) -> LoadLexicalStage:
    stage = LoadLexicalStage()
    chunks = MagicMock(contract="chunks")
    monkeypatch.setattr(stage_module, "corpus_chain", MagicMock())
    monkeypatch.setattr(stage_module, "store_database_url", MagicMock(return_value="pg://store"))
    monkeypatch.setattr(stage_module, "SnapshotValidator", MagicMock())
    monkeypatch.setattr(stage_module, "check_cancelled", MagicMock())
    monkeypatch.setattr(stage_module, "load_summary", _step(events, "summary", {}))
    monkeypatch.setattr(stage_module, "publish_summary", _step(events, "publish", (Path("m"), "d")))
    monkeypatch.setattr(stage, "_load", _step(events, "load", ((chunks,), 0)))
    monkeypatch.setattr(stage, "_build", _step(events, "build", MagicMock()))
    monkeypatch.setattr(stage, "_verify", _step(events, "verify", (MagicMock(ok=True), {})))
    monkeypatch.setattr(stage, "_result", _step(events, "result", "done"))
    return stage


def test_stage_runs_every_store_phase_inside_the_load_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    @contextmanager
    def lock(url: str) -> Iterator[None]:
        events.append(f"lock {url}")
        yield
        events.append("unlock")

    stage = _stage(monkeypatch, events)
    monkeypatch.setattr(stage_module, "exclusive_lexical_load", lock)
    assert stage._run(MagicMock(options={"project_root": "/project"})) == "done"
    assert events == [
        "lock pg://store",
        "load",
        "build",
        "verify",
        "unlock",
        "summary",
        "publish",
        "result",
    ]


def test_refused_lock_loads_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    stage = _stage(monkeypatch, events)
    busy = MagicMock(side_effect=LexicalLoadBusyError("another load-lexical run owns the store"))
    monkeypatch.setattr(stage_module, "exclusive_lexical_load", busy)
    with pytest.raises(LexicalLoadBusyError):
        stage._run(MagicMock(options={"project_root": "/project"}))
    assert events == []

"""Projection retries and cleanup must preserve the active generation."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from arxiv_int.stores.projections import commands, lifecycle
from arxiv_int.stores.projections.model import ProjectionRequest


def test_active_projection_refused_before_preparing_inputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    engine = MagicMock()
    connection = engine.begin.return_value.__enter__.return_value
    connection.execute.return_value.first.return_value = ("lexical:active",)
    monkeypatch.setattr(lifecycle, "create_engine", lambda *a, **k: engine)
    prepared: list[bool] = []
    monkeypatch.setattr(lifecycle, "_prepare_inputs", lambda *a: prepared.append(True) or "failed")
    result = lifecycle.build_projections(
        ProjectionRequest(
            project_root=Path(__file__).parents[3],
            run_id="active",
            kinds=("lexical",),
            database_url="postgresql://fixture@127.0.0.1/fixture",
        )
    )
    assert not prepared
    assert result.status == "failed"
    assert "active" in result.detail


def test_cleanup_command_never_builds(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(commands, "find_project_root", lambda _: tmp_path)
    monkeypatch.setattr(commands, "optional_store_url", lambda _root, explicit=None: None)
    monkeypatch.delenv("ARXIV_INT_MIGRATION_DATABASE_URL", raising=False)
    built: list[bool] = []
    monkeypatch.setattr(commands, "build_projections", lambda *a: built.append(True))
    args = SimpleNamespace(
        store_command="projections-cleanup",
        project_root=tmp_path,
        run_id="cleanup",
        kinds=None,
        apply=False,
    )
    try:
        status = commands.run_projection_command(args)
    except AttributeError:
        status = 1
    assert not built
    assert status == 2


def test_stale_cleanup_plan_does_not_drop_an_active_projection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arxiv_int.stores.projections import cleanup

    dropped: list[str] = []
    monkeypatch.setattr(cleanup, "cleanup_candidates", lambda _: ())
    monkeypatch.setattr(cleanup, "drop_lexical", lambda _, version: dropped.append(version))
    stale = ({"kind": "lexical", "projection_id": "lexical:v1", "status": "retired"},)
    assert cleanup.apply_cleanup(MagicMock(), stale, age_enabled=False) == ()
    assert not dropped


def test_cleanup_kind_filter_preserves_unselected_versions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arxiv_int.stores.projections import cleanup

    candidates = tuple(
        {"kind": kind, "projection_id": f"{kind}:old", "engine_object": f"search.{kind}_p_old"}
        for kind in ("lexical", "vector")
    )
    monkeypatch.setattr(cleanup, "cleanup_candidates", lambda _: candidates)
    planned = cleanup.plan_cleanup(MagicMock(), kinds=("lexical",))
    assert planned == (candidates[0],)

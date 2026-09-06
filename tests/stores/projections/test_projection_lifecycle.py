"""Unit coverage for projection adapters, cleanup, and locked lifecycle paths."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from arxiv_int.contracts.migrations.runner import DATABASE_URL_VARIABLE
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.projections.adapters import lexical, vector
from arxiv_int.stores.projections.adapters.graph import engine_name, sampled_parity
from arxiv_int.stores.projections.cleanup import apply_cleanup, plan_cleanup
from arxiv_int.stores.projections.commands import run_projection_command
from arxiv_int.stores.projections.inputs import require_sources
from arxiv_int.stores.projections.lifecycle import build_projections
from arxiv_int.stores.projections.model import (
    KIND_GRAPH,
    KIND_LEXICAL,
    KIND_VECTOR,
    RUN_FAILED,
    KindBuild,
    ProjectionRequest,
)
from arxiv_int.stores.projections.reconcile import fetch_ids, relation_exists


def _root() -> Path:
    return discover_project_root(Path(__file__))


def test_require_sources_and_fetch_ids_reject_bad_names() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.return_value = False
    with pytest.raises(LookupError, match="missing derived"):
        require_sources(connection, KIND_LEXICAL, "v1")
    with pytest.raises(ValueError, match="qualified table"):
        fetch_ids(connection, "chunks", "chunk_id")
    connection.execute.return_value.scalar.return_value = True
    assert relation_exists(connection, "derived.proj_lexical_rows") is True


def test_vector_empty_source_skips_hnsw() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.side_effect = [0]
    engine_object = vector.build_vector(connection, "v1", "derived.proj_vector_rows")
    assert engine_object == "search.vector_p_v1"
    sql = " ".join(str(call.args[0]) for call in connection.execute.call_args_list)
    assert "hnsw" not in sql.lower()


def test_vector_mixed_dimensions_fail() -> None:
    connection = MagicMock()
    connection.execute.return_value.scalar.side_effect = [2, 3, 2]
    with pytest.raises(ValueError, match="non-mixed"):
        vector.build_vector(connection, "v1", "derived.proj_vector_rows")


def test_drop_lexical_uses_search_schema_index() -> None:
    connection = MagicMock()
    lexical.drop_lexical(connection, "v1")
    sql = " ".join(str(call.args[0]) for call in connection.execute.call_args_list)
    assert "search.lexical_p_v1_bm25" in sql
    assert "DROP TABLE IF EXISTS search.lexical_p_v1" in sql


def test_sampled_parity_without_vertices() -> None:
    ok, reason = sampled_parity(MagicMock(), "v1", (), age_enabled=True)
    assert ok is True
    assert "no vertices" in reason
    assert engine_name(False) == "recursive-sql"
    assert engine_name(True) == "age"


def test_apply_cleanup_dispatches(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[tuple[str, str]] = []
    monkeypatch.setattr(
        "arxiv_int.stores.projections.cleanup.drop_lexical",
        lambda _c, version: seen.append(("lexical", version)),
    )
    monkeypatch.setattr(
        "arxiv_int.stores.projections.cleanup.drop_vector",
        lambda _c, version: seen.append(("vector", version)),
    )
    monkeypatch.setattr(
        "arxiv_int.stores.projections.cleanup.drop_graph_objects",
        lambda _c, version, age_enabled: seen.append(("graph", version)),
    )
    monkeypatch.setattr("arxiv_int.stores.projections.cleanup.mark_dropped", lambda _c, _i: None)
    planned = (
        {
            "projection_id": "lexical:v1",
            "kind": KIND_LEXICAL,
            "engine_object": "x",
            "status": "failed",
        },
        {
            "projection_id": "vector:v1",
            "kind": KIND_VECTOR,
            "engine_object": "x",
            "status": "failed",
        },
        {
            "projection_id": "graph:v1",
            "kind": KIND_GRAPH,
            "engine_object": "x",
            "status": "retired",
        },
    )
    executed = apply_cleanup(MagicMock(), planned, age_enabled=False)
    assert [item[0] for item in seen] == ["lexical", "vector", "graph"]
    assert all(item["status"] == "executed" for item in executed)


def test_plan_cleanup_upserts(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "arxiv_int.stores.projections.cleanup.cleanup_candidates",
        lambda _c: (
            {
                "projection_id": "lexical:v1",
                "kind": KIND_LEXICAL,
                "engine_object": "search.lexical_p_v1",
                "status": "failed",
            },
        ),
    )
    connection = MagicMock()
    planned = plan_cleanup(connection)
    assert planned[0]["projection_id"] == "lexical:v1"
    assert connection.execute.called


def test_build_rejects_invalid_run_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    result = build_projections(ProjectionRequest(run_id="???", project_root=_root()))
    assert result.status == RUN_FAILED
    assert result.activated is False


def test_build_failed_dbt_does_not_activate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://arxiv_int@127.0.0.1/arxiv_int")
    monkeypatch.setattr(
        "arxiv_int.stores.projections.lifecycle._prepare_inputs", lambda *_a: "dbt failed"
    )
    result = build_projections(
        ProjectionRequest(run_id="proj-a", project_root=_root(), activate=True)
    )
    assert result.status == RUN_FAILED
    assert result.activated is False
    assert "dbt failed" in result.detail


def test_build_activates_when_all_kinds_publishable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://arxiv_int@127.0.0.1/arxiv_int")
    monkeypatch.setattr("arxiv_int.stores.projections.lifecycle._prepare_inputs", lambda *_a: None)
    switched: list[str] = []

    def _kind(*_args: object, **kwargs: object) -> KindBuild:
        kind = str(kwargs["kind"])
        return KindBuild(
            kind=kind,
            projection_id=f"{kind}:proj_a",
            version_id="proj_a",
            status="validated",
            engine="paradedb",
            engine_object="obj",
            row_count=1,
            checksum="abc",
            quality_status="pass",
            publishable=True,
            logical_ids=("id-1",),
            detail="ok",
        )

    class _Begin:
        def __enter__(self) -> MagicMock:
            return MagicMock()

        def __exit__(self, *_exc: object) -> bool:
            return False

    engine = MagicMock()
    engine.begin.return_value = _Begin()
    monkeypatch.setattr(
        "arxiv_int.stores.projections.lifecycle.create_engine", lambda *_a, **_k: engine
    )
    monkeypatch.setattr("arxiv_int.stores.projections.lifecycle.build_kind", _kind)
    monkeypatch.setattr(
        "arxiv_int.stores.projections.lifecycle.switch_active",
        lambda _c, **kwargs: switched.append(str(kwargs["kind"])),
    )
    monkeypatch.setattr("arxiv_int.stores.projections.lifecycle.plan_cleanup", lambda _c: ())
    result = build_projections(
        ProjectionRequest(
            run_id="proj-a",
            project_root=_root(),
            kinds=(KIND_LEXICAL,),
            activate=True,
            skip_dbt=True,
        )
    )
    assert result.status == "ok"
    assert result.activated is True
    assert switched == [KIND_LEXICAL]


def test_projection_status_command_without_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    monkeypatch.setattr(
        "arxiv_int.stores.projections.commands.find_project_root", lambda _p: tmp_path
    )
    args = SimpleNamespace(
        store_command="projections-status",
        project_root=tmp_path,
        run_id="r1",
    )
    assert run_projection_command(args) == 2

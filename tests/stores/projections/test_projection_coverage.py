"""Coverage for builder, registry, AGE adapter, and CLI dispatch."""

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from arxiv_int.contracts.migrations.runner import DATABASE_URL_VARIABLE
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.projections import builder, lifecycle
from arxiv_int.stores.projections.adapters import graph, lexical, vector
from arxiv_int.stores.projections.commands import run_projection_command
from arxiv_int.stores.projections.inputs import expected_ids, source_relation
from arxiv_int.stores.projections.lock import ProjectionLock, exclusive_version
from arxiv_int.stores.projections.model import (
    KIND_GRAPH,
    KIND_LEXICAL,
    KIND_VECTOR,
    RUN_FAILED,
    RUN_OK,
    KindBuild,
    ProjectionRequest,
    ProjectionResult,
    exit_status,
)
from arxiv_int.stores.projections.quality import pass_fail
from arxiv_int.stores.projections.reconcile import checksum_for, fetch_ids, fetch_maps, one_hop_sql
from arxiv_int.stores.projections.registry import (
    active_projection_id,
    cleanup_candidates,
    mark_dropped,
    mark_failed,
    record_validation,
    switch_active,
    upsert_staging,
    write_evidence_rows,
)


def _root() -> Path:
    return discover_project_root(Path(__file__))


def _request(**kwargs: object) -> ProjectionRequest:
    values: dict[str, object] = {"run_id": "proj-a", "project_root": _root()}
    values.update(kwargs)
    return ProjectionRequest(**values)  # type: ignore[arg-type]


def test_build_kind_records_failure_when_counts_differ(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "require_sources", lambda *_a, **_k: None)
    monkeypatch.setattr(
        builder, "_materialize", lambda *_a, **_k: ("paradedb", "obj", ("c1", "c2"))
    )
    monkeypatch.setattr(builder, "expected_ids", lambda *_a, **_k: ("c1",))
    monkeypatch.setattr(builder, "upsert_staging", lambda *_a, **_k: None)
    monkeypatch.setattr(builder, "record_validation", lambda *_a, **_k: None)
    monkeypatch.setattr(builder, "write_evidence_rows", lambda *_a, **_k: None)
    monkeypatch.setattr(builder, "mark_failed", lambda *_a, **_k: None)
    monkeypatch.setattr(builder, "relation_exists", lambda *_a, **_k: True)
    result = builder.build_kind(
        MagicMock(),
        _request(),
        Path("."),
        kind=KIND_LEXICAL,
        version_id="v1",
        age_enabled=False,
    )
    assert result.publishable is False
    assert result.status == "failed"


def test_materialize_dispatches_each_kind(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(builder, "build_lexical", lambda *_a, **_k: "lex")
    monkeypatch.setattr(builder, "build_vector", lambda *_a, **_k: "vec")
    monkeypatch.setattr(builder, "build_relational_graph", lambda *_a, **_k: None)
    monkeypatch.setattr(builder, "write_open_exports", lambda *_a, **_k: None)
    monkeypatch.setattr(builder, "load_age_graph", lambda *_a, **_k: "g_v1")
    monkeypatch.setattr(builder, "fetch_ids", lambda *_a, **_k: ("id-1",))
    monkeypatch.setattr(builder, "fetch_maps", lambda *_a, **_k: ())
    monkeypatch.setattr(builder, "source_relation", lambda *_a, **_k: "derived.x")
    conn = MagicMock()
    assert builder._materialize(conn, KIND_LEXICAL, "v1", False, Path("."))[0] == "paradedb"
    assert builder._materialize(conn, KIND_VECTOR, "v1", False, Path("."))[0] == "pgvector"
    engine, obj, _ids = builder._materialize(conn, KIND_GRAPH, "v1", True, Path("."))
    assert engine == "age"
    assert obj == "g_v1"


def test_registry_and_reconcile_helpers() -> None:
    connection = MagicMock()
    connection.execute.return_value.first.return_value = None
    upsert_staging(
        connection,
        projection_id="lexical:v1",
        kind="lexical",
        version_id="v1",
        engine="paradedb",
        engine_object="obj",
        run_id="r1",
        schema_version="1.0.0",
    )
    record_validation(
        connection,
        projection_id="lexical:v1",
        status="validated",
        row_count=1,
        checksum="x",
        quality_status="pass",
        input_fingerprint="f",
    )
    write_evidence_rows(
        connection, "lexical:v1", [{"check_name": "projection.row_count", "status": "pass"}]
    )
    switch_active(connection, kind="lexical", projection_id="lexical:v1", publishable=True)
    connection.execute.return_value.first.return_value = ("lexical:v1",)
    assert active_projection_id(connection, "lexical") == "lexical:v1"
    switch_active(connection, kind="lexical", projection_id="lexical:v1", publishable=True)
    connection.execute.return_value.first.return_value = ("lexical:v0",)
    switch_active(connection, kind="lexical", projection_id="lexical:v1", publishable=True)
    mark_failed(connection, "lexical:v1", "fail")
    mark_dropped(connection, "lexical:v1")
    active_rows = MagicMock()
    active_rows.__iter__.return_value = iter([("lexical:v0",)])
    retired = MagicMock()
    retired.fetchall.return_value = [
        ("lexical:v1", "lexical", "obj", "failed"),
        ("lexical:v0", "lexical", "obj", "retired"),
    ]
    connection.execute.side_effect = [active_rows, retired]
    planned = cleanup_candidates(connection)
    assert planned[0]["projection_id"] == "lexical:v1"
    connection.execute.side_effect = None
    connection.execute.return_value.fetchall.return_value = [("c1",)]
    assert fetch_ids(connection, "search.lexical_p_v1", "chunk_id") == ("c1",)
    connection.execute.return_value.fetchall.return_value = [("a", "b")]
    assert one_hop_sql(connection, "search.graph_p_v1_edges", "a") == (("a", "b"),)
    connection.execute.return_value.mappings.return_value = [{"object_id": "o1"}]
    assert (
        fetch_maps(connection, "search.graph_p_v1_vertices", ("object_id",))[0]["object_id"] == "o1"
    )
    assert checksum_for(("b", "a")) == checksum_for(("a", "b"))
    assert pass_fail(False, checked=1) == "fail"


def test_graph_age_and_sql_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    age = MagicMock()
    age.execute.return_value.scalar.return_value = True

    @contextmanager
    def _session(_connection: object) -> object:
        yield age

    monkeypatch.setattr(graph, "_age_autocommit", _session)
    monkeypatch.setattr(
        graph,
        "fetch_maps",
        MagicMock(
            side_effect=[
                (
                    {
                        "object_id": "o1",
                        "object_type": "org",
                        "preferred_label": "A",
                        "review_state": None,
                    },
                ),
                (
                    {
                        "fact_id": "f1",
                        "subject_object_id": "o1",
                        "object_object_id": "o2",
                        "predicate_id": "rel",
                    },
                ),
            ]
        ),
    )
    age.exec_driver_sql.return_value.all.return_value = [("o1", "o2")]
    assert graph.load_age_graph(MagicMock(), "v1") == "g_v1"
    assert age.exec_driver_sql.called
    graph.drop_graph_objects(MagicMock(), "v1", age_enabled=True)
    conn = MagicMock()
    graph.build_relational_graph(
        conn, "v1", "derived.proj_graph_vertices", "derived.proj_graph_edges"
    )
    monkeypatch.setattr(graph, "one_hop_sql", lambda *_a, **_k: (("o1", "o2"),))
    monkeypatch.setattr(graph, "cypher_one_hop", lambda *_a, **_k: (("o1", "o2"),))
    ok, reason = graph.sampled_parity(conn, "v1", ("o1",), age_enabled=True)
    assert ok is True
    assert "match" in reason
    monkeypatch.setattr(graph, "cypher_one_hop", lambda *_a, **_k: (("x", "y"),))
    ok, _reason = graph.sampled_parity(conn, "v1", ("o1",), age_enabled=True)
    assert ok is False
    lexical.build_lexical(conn, "v1", "derived.proj_lexical_rows")
    vector_conn = MagicMock()
    vector_conn.execute.return_value.scalar.side_effect = [2, 3, 1]
    vector.build_vector(vector_conn, "v1", "derived.proj_vector_rows")
    vector.drop_vector(vector_conn, "v1")
    assert source_relation(KIND_VECTOR, "v1").endswith("proj_vector_rows__g_v1")
    assert source_relation(KIND_GRAPH, "v1").endswith("proj_graph_vertices__g_v1")
    assert expected_ids.__name__ == "expected_ids"


def test_lifecycle_lock_publish_and_sql_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://arxiv_int@127.0.0.1/arxiv_int")
    monkeypatch.setattr(
        lifecycle,
        "exclusive_version",
        lambda *_a, **_k: (_ for _ in ()).throw(lifecycle.ProjectionLockError("owned")),
    )
    locked = lifecycle.build_projections(_request())
    assert locked.status == RUN_FAILED
    monkeypatch.setattr(lifecycle, "exclusive_version", exclusive_version)
    monkeypatch.setattr(lifecycle, "_prepare_inputs", lambda *_a: None)

    class _Begin:
        def __enter__(self) -> MagicMock:
            raise SQLAlchemyError("boom")

        def __exit__(self, *_exc: object) -> bool:
            return False

    engine = MagicMock()
    engine.begin.return_value = _Begin()
    monkeypatch.setattr(lifecycle, "create_engine", lambda *_a, **_k: engine)
    failed = lifecycle.build_projections(_request(activate=True, skip_dbt=True))
    assert failed.status == RUN_FAILED
    monkeypatch.setattr(
        lifecycle,
        "build_kind",
        lambda *_a, **_k: KindBuild(
            kind=KIND_LEXICAL,
            projection_id="lexical:proj_a",
            version_id="proj_a",
            status="validated",
            engine="paradedb",
            engine_object="obj",
            row_count=1,
            checksum="abc",
            quality_status="pass",
            publishable=True,
            logical_ids=("c1",),
            detail="ok",
        ),
    )

    class _Ok:
        def __enter__(self) -> MagicMock:
            return MagicMock()

        def __exit__(self, *_exc: object) -> bool:
            return False

    engine.begin.return_value = _Ok()
    monkeypatch.setattr(lifecycle, "switch_active", lambda *_a, **_k: None)
    monkeypatch.setattr(lifecycle, "plan_cleanup", lambda _c: ({"projection_id": "x"},))
    monkeypatch.setattr(lifecycle, "apply_cleanup", lambda *_a, **_k: ({"status": "executed"},))
    published = lifecycle.build_projections(
        _request(
            activate=True,
            skip_dbt=True,
            apply_cleanup=True,
            publish=True,
            runs_dir=tmp_path / "runs",
            kinds=(KIND_LEXICAL,),
        )
    )
    assert published.status == RUN_OK
    assert published.published_manifest_dir
    monkeypatch.setattr(
        "arxiv_int.transformations.runner.run_transform",
        lambda _req: SimpleNamespace(ok=True, detail=""),
    )
    assert lifecycle._prepare_inputs(_request(skip_dbt=False), "postgresql://x") is None
    monkeypatch.setattr(
        "arxiv_int.stores.projections.lifecycle.load_age_compatibility",
        lambda _root: SimpleNamespace(age_enabled=False),
    )
    assert lifecycle._age_enabled(_request(age_enabled=None)) is False


def test_commands_build_cleanup_and_status(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "arxiv_int.stores.projections.commands.find_project_root", lambda _p: tmp_path
    )
    monkeypatch.setattr(
        "arxiv_int.stores.projections.commands.build_projections",
        lambda _req: ProjectionResult(
            status=RUN_FAILED,
            command="build",
            run_id="r1",
            version_id="r1",
            activatable=False,
            activated=False,
            detail="nope",
            artifact_dir=".",
        ),
    )
    args = SimpleNamespace(
        store_command="projections-build",
        project_root=tmp_path,
        run_id="r1",
        kinds=None,
        activate=False,
        publish=False,
        runs_dir=None,
        skip_dbt=True,
        apply=False,
        age_enabled=None,
    )
    assert run_projection_command(args) == 1
    args.store_command = "projections-cleanup"
    args.apply = True
    monkeypatch.setattr("arxiv_int.stores.projections.commands._run_cleanup", lambda *_a, **_k: 1)
    assert run_projection_command(args) == 1
    monkeypatch.setattr(
        "arxiv_int.stores.projections.commands.resolve_database_url", lambda: "postgresql://x"
    )
    engine = MagicMock()
    engine.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = [
        ("lexical", "lexical:v1", "active")
    ]
    monkeypatch.setattr(
        "arxiv_int.stores.projections.commands.create_engine", lambda *_a, **_k: engine
    )
    args.store_command = "projections-status"
    assert run_projection_command(args) == 0
    engine.connect.return_value.__enter__.return_value.execute.return_value.fetchall.return_value = []
    assert run_projection_command(args) == 0
    monkeypatch.setattr(
        "arxiv_int.stores.projections.commands.find_project_root",
        lambda _p: (_ for _ in ()).throw(RuntimeError("bad root")),
    )
    assert run_projection_command(args) == 1
    lock = ProjectionLock(MagicMock(), tmp_path / "l")
    lock._handle = None
    lock.release()
    assert (
        exit_status(
            ProjectionResult(
                status="not-run",
                command="build",
                run_id="r",
                version_id="v",
                activatable=False,
                activated=False,
                detail="",
                artifact_dir=".",
            )
        )
        == 2
    )
    assert ProjectionResult(
        status=RUN_OK,
        command="build",
        run_id="r",
        version_id="v",
        activatable=True,
        activated=True,
        detail="",
        artifact_dir=".",
    ).ok

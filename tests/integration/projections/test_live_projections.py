"""Declared live projection rebuild, refusal, and graph-disabled exports."""

import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from arxiv_int.contracts.lint import contracts_root_for
from arxiv_int.contracts.sqlalchemy.model import load_schema_model_from_root
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.apply import apply_revisions
from arxiv_int.stores.postgres.disposable import disposable_store, image_present
from arxiv_int.stores.postgres.load import load_canonical_batch
from arxiv_int.stores.postgres_image.pins import load_image_pins
from arxiv_int.stores.projections.lifecycle import build_projections
from arxiv_int.stores.projections.model import KIND_GRAPH, KIND_LEXICAL, ProjectionRequest
from arxiv_int.stores.projections.paths import export_dir, projection_artifact_dir
from arxiv_int.stores.projections.registry import active_projection_id

pytestmark = [
    pytest.mark.heavy,
    pytest.mark.skipif(shutil.which("docker") is None, reason="docker unavailable"),
    pytest.mark.skipif(
        os.environ.get("ARXIV_INT_RUN_PROJECTIONS") != "1",
        reason="set ARXIV_INT_RUN_PROJECTIONS=1 for the declared disposable projection run",
    ),
]


def _root() -> Path:
    return discover_project_root(Path(__file__))


def _load(url: str, contract_id: str, rows: list[dict[str, object]], run_id: str) -> None:
    root = _root()
    model = load_schema_model_from_root(contracts_root_for(root))
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            load_canonical_batch(
                connection, model, contract_id, rows, project_root=root, run_id=run_id
            )
    finally:
        engine.dispose()


def _seed(url: str) -> None:
    _load(
        url,
        "documents",
        [
            {
                "document_id": "doc-1",
                "generation_id": "gen-1",
                "contract_version": "1.0.0",
                "title": "Nasos",
                "language": "ru",
            }
        ],
        "seed-docs",
    )
    _load(
        url,
        "chunks",
        [
            {
                "chunk_id": "chunk-1",
                "document_id": "doc-1",
                "generation_id": "gen-1",
                "contract_version": "1.0.0",
                "text": "nasos model P-100",
                "chunker_id": "sent-1",
            }
        ],
        "seed-chunks",
    )
    _load(
        url,
        "objects",
        [
            {
                "object_id": "obj-1",
                "generation_id": "gen-1",
                "contract_version": "1.0.0",
                "object_type": "org",
                "preferred_label": "Acme",
            },
            {
                "object_id": "obj-2",
                "generation_id": "gen-1",
                "contract_version": "1.0.0",
                "object_type": "product",
                "preferred_label": "Pump",
            },
        ],
        "seed-objects",
    )
    _load(
        url,
        "facts",
        [
            {
                "fact_id": "fact-1",
                "subject_object_id": "obj-1",
                "predicate_id": "supplies",
                "object_object_id": "obj-2",
                "status": "accepted",
                "document_id": "doc-1",
                "extractor_id": "rule-1",
                "generation_id": "gen-1",
                "contract_version": "1.0.0",
            }
        ],
        "seed-facts",
    )
    engine = create_engine(url)
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    "INSERT INTO search.embedding_profiles "
                    "(profile_id, dimensions, model_digest, contract_version) "
                    "VALUES ('p1', 3, 'digest-a', '1.0.0')"
                )
            )
            connection.execute(
                text(
                    "INSERT INTO search.embeddings ("
                    "embedding_id, target_kind, target_id, profile_id, dimensions, "
                    "vector_ref, model_digest, generation_id, contract_version) VALUES "
                    "('emb-1', 'chunk', 'chunk-1', 'p1', 3, '[1,0,0]', 'digest-a', "
                    "'gen-1', '1.0.0'), "
                    "('emb-2', 'chunk', 'chunk-2', 'p1', 3, '[0,1,0]', 'digest-a', "
                    "'gen-1', '1.0.0')"
                )
            )
    finally:
        engine.dispose()


def _build(
    url: str, run_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kwargs: object
) -> object:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    return build_projections(
        ProjectionRequest(
            run_id=run_id,
            project_root=_root(),
            database_url=url,
            **kwargs,  # type: ignore[arg-type]
        )
    )


def _ok_build(
    url: str, run_id: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, **kwargs: object
) -> object:
    result = _build(url, run_id, tmp_path, monkeypatch, **kwargs)
    assert result.status == "ok", result.detail
    return result


def _lexical_pointer(url: str) -> str | None:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return active_projection_id(connection, KIND_LEXICAL)
    finally:
        engine.dispose()


def _document_count(url: str) -> int:
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            return int(
                connection.execute(text("SELECT count(*) FROM corpus.documents")).scalar() or 0
            )
    finally:
        engine.dispose()


def test_rebuild_ids_failure_does_not_replace_and_graph_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _root()
    pins = load_image_pins(root)
    if not image_present(pins.local_image_ref):
        pytest.skip(f"image {pins.local_image_ref} is not present; build it first")
    with disposable_store(root, tmp_path / "pgdata", pins=pins) as store:
        assert apply_revisions(root, url=store.url, run_id="proj-schema", revision="head").ok
        _seed(store.url)
        first = _ok_build(store.url, "proj-a", tmp_path, monkeypatch, activate=True)
        assert first.activated is True
        checksums = {item.kind: item.checksum for item in first.kinds}
        assert checksums[KIND_LEXICAL]
        assert _lexical_pointer(store.url) == "lexical:proj_a"
        second = _ok_build(store.url, "proj-b", tmp_path, monkeypatch, activate=True)
        assert second.activated is True
        assert {item.kind: item.checksum for item in second.kinds} == checksums
        active = _lexical_pointer(store.url)
        assert active == "lexical:proj_b"
        failed = _build(store.url, "proj-fail", tmp_path, monkeypatch, skip_dbt=True, activate=True)
        assert failed.status == "failed"
        assert failed.activated is False
        assert _lexical_pointer(store.url) == active
        assert _document_count(store.url) == 1
        disabled = _ok_build(
            store.url,
            "proj-sql",
            tmp_path,
            monkeypatch,
            kinds=(KIND_GRAPH,),
            age_enabled=False,
            activate=True,
        )
        assert disabled.kinds[0].engine == "recursive-sql"
        exports = export_dir(projection_artifact_dir(root, "proj-sql"))
        assert (exports / "graph.graphml").is_file()
        assert (exports / "graph.jsonld").is_file()
        assert (exports / "graph.ttl").is_file()
        _assert_active_retry_and_cleanup(store.url, tmp_path, monkeypatch)


def _assert_active_retry_and_cleanup(
    url: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from types import SimpleNamespace

    from arxiv_int.stores.projections.commands import run_projection_command

    evidence = projection_artifact_dir(_root(), "proj-b") / "result.json"
    before = evidence.read_bytes()
    refused = _build(url, "proj-b", tmp_path, monkeypatch, activate=True)
    assert refused.status == "failed"
    assert "immutable" in refused.detail
    assert evidence.read_bytes() == before
    assert _lexical_pointer(url) == "lexical:proj_b"
    monkeypatch.setenv("ARXIV_INT_MIGRATION_DATABASE_URL", url)
    args = SimpleNamespace(
        store_command="projections-cleanup",
        project_root=_root(),
        run_id="cleanup",
        kinds=None,
        apply=True,
    )
    assert run_projection_command(args) == 0
    assert _lexical_pointer(url) == "lexical:proj_b"
    assert _document_count(url) == 1
    engine = create_engine(url)
    try:
        with engine.connect() as connection:
            assert (
                connection.execute(text("SELECT to_regclass('search.lexical_p_proj_a')")).scalar()
                is None
            )
            assert (
                connection.execute(text("SELECT count(*) FROM search.lexical_p_proj_b")).scalar()
                == 1
            )
    finally:
        engine.dispose()

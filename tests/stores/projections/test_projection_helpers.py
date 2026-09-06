"""Additional unit coverage for projection helpers that do not need a live store."""

from pathlib import Path

import pytest

from arxiv_int.contracts.migrations.runner import DATABASE_URL_VARIABLE
from arxiv_int.data_quality.model import STATUS_NOT_APPLICABLE
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.projections.adapters.lexical import TOKENIZER_PROFILE, engine_name
from arxiv_int.stores.projections.adapters.vector import engine_name as vector_engine
from arxiv_int.stores.projections.artifacts import publish_result, write_result
from arxiv_int.stores.projections.ids import cypher_string, derived_relation, projection_id
from arxiv_int.stores.projections.inputs import MODEL_LEXICAL, source_relation
from arxiv_int.stores.projections.lock import (
    ProjectionLockError,
    exclusive_version,
    try_acquire_version_lock,
)
from arxiv_int.stores.projections.model import (
    KIND_GRAPH,
    KIND_LEXICAL,
    RUN_FAILED,
    RUN_OK,
    ProjectionRequest,
    ProjectionResult,
    exit_status,
)
from arxiv_int.stores.projections.quality import RULE_PARITY, evidence_maps, not_applicable
from arxiv_int.stores.projections.reconcile import counts_match, sample_starts


def test_helper_identities_and_exit_codes() -> None:
    assert projection_id("lexical", "v1") == "lexical:v1"
    assert derived_relation(MODEL_LEXICAL, "v1") == "derived.proj_lexical_rows__g_v1"
    assert source_relation(KIND_LEXICAL, "v1").endswith("proj_lexical_rows__g_v1")
    assert source_relation(KIND_GRAPH, "v1", edges=True).endswith("proj_graph_edges__g_v1")
    assert engine_name() == "paradedb"
    assert vector_engine() == "pgvector"
    assert "Russian" in TOKENIZER_PROFILE
    assert "keyword" in TOKENIZER_PROFILE
    assert cypher_string("a'b") == "a\\'b"
    assert counts_match(["a", "b"], ["b", "a"])
    assert not counts_match(["a"], ["a", "b"])
    assert sample_starts(["c", "a", "b"], limit=2)[0] == "a"
    skipped = not_applicable(RULE_PARITY, "AGE disabled")
    assert skipped.status == STATUS_NOT_APPLICABLE
    from arxiv_int.data_quality.model import STATUS_PASS
    from arxiv_int.stores.projections.quality import (
        RULE_CHECKSUM,
        RULE_ENGINE,
        RULE_ROW_COUNT,
        assemble_result,
        check_result,
    )

    mapped = evidence_maps(
        assemble_result(
            KIND_LEXICAL,
            (
                check_result(RULE_ROW_COUNT, status=STATUS_PASS, checked_count=1),
                check_result(RULE_CHECKSUM, status=STATUS_PASS, checked_count=1),
                skipped,
                check_result(RULE_ENGINE, status=STATUS_PASS, checked_count=1),
            ),
            checked_rows=1,
            fingerprint_parts=("lexical", "v1"),
        )
    )
    assert mapped[2]["check_name"] == RULE_PARITY
    assert (
        exit_status(
            ProjectionResult(
                status=RUN_OK,
                command="build",
                run_id="r",
                version_id="v",
                activatable=True,
                activated=False,
                detail="",
                artifact_dir=".",
            )
        )
        == 0
    )
    assert (
        exit_status(
            ProjectionResult(
                status=RUN_FAILED,
                command="build",
                run_id="r",
                version_id="v",
                activatable=False,
                activated=False,
                detail="x",
                artifact_dir=".",
            )
        )
        == 1
    )


def test_lock_and_publish(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    root = discover_project_root(Path(__file__))
    held = try_acquire_version_lock(root, "vlock")
    try:
        with pytest.raises(ProjectionLockError):
            try_acquire_version_lock(root, "vlock")
    finally:
        held.release()
    with exclusive_version(root, "vlock2"):
        pass
    result = ProjectionResult(
        status=RUN_OK,
        command="build",
        run_id="pub",
        version_id="pub",
        activatable=True,
        activated=False,
        detail="ok",
        artifact_dir=str(tmp_path / "art"),
    )
    write_result(tmp_path / "art", result)
    published = publish_result(
        ProjectionRequest(
            run_id="pub",
            project_root=root,
            publish=True,
            runs_dir=tmp_path / "runs",
        ),
        tmp_path / "art",
    )
    assert published is not None
    assert (published / "projections.json").is_file()
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)

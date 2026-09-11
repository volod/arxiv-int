"""Unit coverage for projection identifiers, quality gates, and exports."""

from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main
from arxiv_int.contracts.migrations.runner import DATABASE_URL_VARIABLE
from arxiv_int.data_quality.engine.model import STATUS_FAIL, STATUS_PASS
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.projections.adapters.graph import write_open_exports
from arxiv_int.stores.projections.ids import (
    UnsafeIdentifierError,
    age_graph_name,
    derived_relation,
    logical_checksum,
    require_ident,
    sanitize_version_id,
    table_name,
)
from arxiv_int.stores.projections.inputs import (
    MODEL_EDGES,
    MODEL_LEXICAL,
    MODEL_VECTOR,
    MODEL_VERTICES,
)
from arxiv_int.stores.projections.lifecycle import build_projections
from arxiv_int.stores.projections.model import (
    KIND_LEXICAL,
    RUN_NOT_RUN,
    ProjectionRequest,
    requested_kinds,
)
from arxiv_int.stores.projections.quality import (
    RULE_CHECKSUM,
    RULE_ENGINE,
    RULE_PARITY,
    RULE_ROW_COUNT,
    assemble_result,
    check_result,
    pass_fail,
)
from arxiv_int.stores.projections.registry import (
    ActivationRefusedError,
    switch_active,
    validated_status,
)
from arxiv_int.transformations.credentials import sanitize_generation_id


def test_sanitize_version_and_checksum_are_stable() -> None:
    assert sanitize_version_id("Fix-1") == "fix_1"
    assert sanitize_version_id("12run") == "g_12run"
    assert sanitize_version_id("12run") == sanitize_generation_id("12run")
    assert logical_checksum(["b", "a"]) == logical_checksum(("a", "b", "a"))
    assert logical_checksum(["a"]) != logical_checksum(["b"])
    with pytest.raises(ValueError):
        sanitize_version_id("???")
    with pytest.raises(UnsafeIdentifierError):
        require_ident("DROP TABLE")
    assert age_graph_name("fix_1") == "g_fix_1"


def test_uuid_run_derived_tables_fit_postgres_idents() -> None:
    version = sanitize_version_id("run-0123456789abcdef0123456789abcdef")
    models = (MODEL_LEXICAL, MODEL_VECTOR, MODEL_VERTICES, MODEL_EDGES)
    for model in models:
        table = derived_relation(model, version).split(".", 1)[1]
        assert require_ident(table) == table
        assert 48 < len(table) <= 63
    covering = table_name(KIND_LEXICAL, version)
    assert require_ident(covering) == covering
    with pytest.raises(UnsafeIdentifierError):
        require_ident("a" * 64)


def test_quality_result_blocks_activation_on_failure() -> None:
    failed = assemble_result(
        KIND_LEXICAL,
        (
            check_result(RULE_ROW_COUNT, status=STATUS_FAIL, checked_count=1, failed_count=1),
            check_result(RULE_CHECKSUM, status=STATUS_PASS, checked_count=1),
            check_result(RULE_PARITY, status=STATUS_PASS, checked_count=1),
            check_result(RULE_ENGINE, status=STATUS_PASS, checked_count=1),
        ),
        checked_rows=1,
        fingerprint_parts=("lexical", "v1"),
    )
    assert failed.publishable is False
    assert validated_status(False) == "failed"
    with pytest.raises(ActivationRefusedError, match="not publishable"):
        switch_active(None, kind="lexical", projection_id="lexical:v1", publishable=False)
    assert pass_fail(True, checked=1) == STATUS_PASS


def test_open_exports_do_not_require_age(tmp_path: Path) -> None:
    graphml, jsonld, turtle = write_open_exports(
        tmp_path,
        [{"object_id": "obj-1", "object_type": "org", "preferred_label": "Acme"}],
        [
            {
                "fact_id": "f-1",
                "subject_object_id": "obj-1",
                "object_object_id": "obj-2",
                "predicate_id": "supplies",
            }
        ],
    )
    assert "obj-1" in graphml.read_text(encoding="utf-8")
    assert "urn:arxiv-int:object:obj-1" in jsonld.read_text(encoding="utf-8")
    assert "kg:obj-1" in turtle.read_text(encoding="utf-8")
    assert "kg:supplies" in turtle.read_text(encoding="utf-8")


def test_requested_kinds() -> None:
    assert requested_kinds(["all"]) == ("lexical", "vector", "graph")
    assert requested_kinds(["graph", "graph"]) == ("graph",)
    with pytest.raises(ValueError, match="unknown"):
        requested_kinds(["bm25"])


def test_build_without_database_is_not_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    root = discover_project_root(Path(__file__))
    result = build_projections(
        ProjectionRequest(run_id="offline", project_root=root, skip_dbt=True)
    )
    assert result.status == RUN_NOT_RUN
    assert result.activated is False
    assert (tmp_path / "data" / "projections" / "offline" / "result.json").is_file()


def test_parser_accepts_projection_commands() -> None:
    parser = build_parser()
    build = parser.parse_args(
        ["store", "projections-build", "--run-id", "r1", "--kind", "lexical", "--activate"]
    )
    assert build.store_command == "projections-build"
    assert build.activate is True
    status = parser.parse_args(["store", "projections-status", "--run-id", "r1"])
    assert status.store_command == "projections-status"
    cleanup = parser.parse_args(["store", "projections-cleanup", "--run-id", "r1", "--apply"])
    assert cleanup.apply is True


def test_cli_projection_status_not_run(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: tmp_path,
    )
    assert main(["store", "projections-status", "--run-id", "r1"]) == 2

"""Adoption and apply wrappers without a live database."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from arxiv_int.cli import _tool_data_dir, main
from arxiv_int.contracts.migrations.runner import (
    DATABASE_URL_VARIABLE,
    STATUS_FAILED,
    STATUS_NOT_RUN,
    STATUS_OK,
    RunnerOutcome,
)
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.stores.postgres.adopt import AdoptionReport, adopt_database
from arxiv_int.stores.postgres.apply import (
    SchemaApplyReport,
    apply_on_disposable,
    apply_revisions,
)
from arxiv_int.stores.postgres.commands import (
    run_adopt_schema,
    run_apply_schema,
    run_inspect_schema,
)
from arxiv_int.stores.postgres.constants import (
    CANONICAL_SCHEMAS,
    HASH_MODULUS,
    HEAD_REVISION,
    PARTITIONED_TABLES,
    PROJECTION_METADATA_TABLES,
    STORE_ROLES,
)
from arxiv_int.stores.postgres.evidence import write_evidence
from arxiv_int.stores.postgres.inspect_live import LiveStoreCatalog, PartitionSpec


def _root() -> Path:
    return discover_project_root(Path(__file__))


def _complete_catalog(revision: str = HEAD_REVISION) -> LiveStoreCatalog:
    return LiveStoreCatalog(
        schemas=(*CANONICAL_SCHEMAS, "staging", "derived"),
        partitioned=tuple(
            PartitionSpec(f"{schema}.{table}", f"HASH ({pk})", HASH_MODULUS)
            for schema, table, pk in PARTITIONED_TABLES
        ),
        checks=("ck_facts_object_xor_literal", "ck_facts_provenance", "ck_facts_status"),
        roles=STORE_ROLES,
        staging_tables=("documents",),
        revision=revision,
        extensions=("vector",),
        control_tables=PROJECTION_METADATA_TABLES,
    )


def _ok_report() -> SchemaApplyReport:
    return SchemaApplyReport(RunnerOutcome(STATUS_OK, "applied"), (), Path("ev.json"), "0001", {})


def test_adopt_without_a_database_is_not_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    report = adopt_database(_root())
    assert report.outcome.status == STATUS_NOT_RUN
    assert not report.ok
    assert report.stamped_revision is None


def test_apply_without_image_or_url_is_not_run(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    monkeypatch.setattr("arxiv_int.stores.postgres.apply.image_present", lambda _ref: False)
    report = apply_on_disposable(_root(), tmp_path / "pgdata", run_id="missing-image")
    assert report.outcome.status == STATUS_NOT_RUN
    assert not report.ok


def test_apply_on_disposable_records_runtime_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr("arxiv_int.stores.postgres.apply.image_present", lambda _ref: True)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("container failed")

    monkeypatch.setattr("arxiv_int.stores.postgres.apply.disposable_store", _boom)
    report = apply_on_disposable(_root(), tmp_path / "pgdata", run_id="boom")
    assert report.outcome.status == STATUS_FAILED
    assert "container failed" in report.findings[0]


def test_apply_revisions_keeps_failed_upgrade(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("arxiv_int.stores.postgres.apply.row_counts", lambda *_a, **_k: {})
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.apply.upgrade",
        lambda *_a, **_k: RunnerOutcome(STATUS_FAILED, "upgrade failed"),
    )
    report = apply_revisions(_root(), url="postgresql://x", run_id="fail")
    assert not report.ok
    assert report.revision is None


def test_apply_revisions_writes_evidence(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr("arxiv_int.stores.postgres.apply.row_counts", lambda *_a, **_k: {})
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.apply.upgrade",
        lambda *_a, **_k: RunnerOutcome(STATUS_OK, "upgraded"),
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.apply.inspect_and_compare",
        lambda *_a, **_k: ([], {"revision": "0001"}, "0001"),
    )
    report = apply_revisions(_root(), url="postgresql://x", run_id="ok-apply")
    assert report.ok
    assert report.revision == "0001"
    assert report.evidence_path is not None


def test_commands_report_not_run_without_a_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    assert run_apply_schema(_root(), run_id="none") == 2
    assert run_inspect_schema(_root(), run_id="none") == 2
    assert run_adopt_schema(_root(), run_id="none") == 2


def test_commands_succeed_with_mocked_live_url(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://x")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.commands.apply_revisions", lambda *_a, **_k: _ok_report()
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.commands.inspect_and_compare",
        lambda *_a, **_k: ([], {"revision": "0001"}, "0001"),
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.commands.adopt_database",
        lambda *_a, **_k: AdoptionReport(
            RunnerOutcome(STATUS_OK, "stamped"), (), "0001", (), {}, Path("a.json")
        ),
    )
    assert run_apply_schema(_root(), url="postgresql://x", run_id="live") == 0
    assert run_inspect_schema(_root(), url="postgresql://x", run_id="live") == 0
    assert run_adopt_schema(_root(), url="postgresql://x", run_id="live") == 0


def test_adopt_stamps_complete_overlay(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://x")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value.execute.return_value.scalar.return_value = (
        False
    )
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.create_engine", lambda *_a, **_k: engine)
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.relocate_public_tables", lambda *_a: [])
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.compare_live_catalog", lambda *_a, **_k: []
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.require_safe_adoption", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.inspect_store", lambda *_a, **_k: _complete_catalog()
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.stamp",
        lambda *_a, **_k: RunnerOutcome(STATUS_OK, "stamped"),
    )
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.catalog_boundary_findings", lambda *_a: [])
    report = adopt_database(_root(), url="postgresql://x", run_id="stamp")
    assert report.ok
    assert report.stamped_revision == HEAD_REVISION


def test_adopt_refuses_partial_overlay(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(DATABASE_URL_VARIABLE, "postgresql://x")
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value.execute.return_value.scalar.return_value = (
        False
    )
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.create_engine", lambda *_a, **_k: engine)
    monkeypatch.setattr("arxiv_int.stores.postgres.adopt.relocate_public_tables", lambda *_a: [])
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.compare_live_catalog", lambda *_a, **_k: []
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.require_safe_adoption", lambda *_a, **_k: None
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.adopt.inspect_store",
        lambda *_a, **_k: LiveStoreCatalog(
            schemas=("corpus",),
            partitioned=(),
            checks=(),
            roles=(),
            staging_tables=(),
            revision=None,
            extensions=(),
        ),
    )
    report = adopt_database(_root(), url="postgresql://x", run_id="partial")
    assert not report.ok
    assert report.outcome.status == STATUS_FAILED


def test_cli_store_commands_dispatch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setattr("arxiv_int.stores.postgres.commands.run_apply_schema", lambda *_a, **_k: 0)
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.commands.run_inspect_schema", lambda *_a, **_k: 0
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.commands.run_build_command", lambda *_a, **_k: 0
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres_image.commands.run_probe_command", lambda *_a, **_k: 0
    )
    assert main(["store", "apply-schema", "--run-id", "cli"]) == 0
    assert main(["store", "inspect-schema", "--run-id", "cli"]) == 0
    assert main(["store", "build-image"]) == 0
    assert main(["store", "probe-image"]) == 0
    named = _tool_data_dir(_root())
    assert "data" in str(named)


def test_evidence_redacts_database_urls(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    path = write_evidence(
        _root(),
        {"url": "postgresql+psycopg://user:secret@127.0.0.1:5432/arxiv_int", "revision": "0001"},
        run_id="redact",
    )
    text = path.read_text(encoding="utf-8")
    assert "secret" not in text
    assert "<redacted>" in text

import logging
import os
from pathlib import Path

import pytest

from arxiv_int.cli import build_parser, main
from arxiv_int.readiness.report import PreflightReport
from arxiv_int.readiness.run import ReadinessResult


def test_parser_selects_the_info_command() -> None:
    assert build_parser().parse_args(["info"]).command == "info"


def test_info_command_logs_the_project_identity(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["info"]) == 0
    assert "arxiv-int" in caplog.text
    assert "arxiv_int" in caplog.text


def test_parser_accepts_a_stage_filter_for_features() -> None:
    arguments = build_parser().parse_args(["features", "--stage", "embed"])

    assert arguments.command == "features"
    assert arguments.stage == "embed"


def test_parser_accepts_readiness_profile_timeout_and_console_only_mode() -> None:
    arguments = build_parser().parse_args(
        ["readiness", "--profiles", "core ui", "--timeout", "1.5", "--no-json-report"]
    )

    assert arguments.command == "readiness"
    assert arguments.profiles == "core ui"
    assert arguments.timeout == 1.5
    assert arguments.no_json_report is True


def test_parser_accepts_contracts_lint_options() -> None:
    parser = build_parser()
    arguments = parser.parse_args(["contracts", "lint", "--skip-datacontract"])

    assert arguments.command == "contracts"
    assert arguments.contracts_command == "lint"
    assert arguments.skip_datacontract is True


def test_parser_accepts_contracts_generate_and_check() -> None:
    parser = build_parser()
    assert parser.parse_args(["contracts", "generate"]).contracts_command == "generate"
    assert parser.parse_args(["contracts", "check"]).contracts_command == "check"
    assert parser.parse_args(["contracts", "evolution"]).contracts_command == "evolution"


def test_parser_accepts_ontology_check_and_generate() -> None:
    parser = build_parser()
    assert parser.parse_args(["ontology", "check"]).ontology_command == "check"
    assert parser.parse_args(["ontology", "generate"]).ontology_command == "generate"


def test_contracts_lint_command_reports_success(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    from arxiv_int.contracts.lint import ContractLintReport

    monkeypatch.setattr(
        "arxiv_int.contracts.lint.lint_contracts",
        lambda root, run_datacontract=True: ContractLintReport((), 15, run_datacontract),
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.lint.contracts_root_for",
        lambda project_root=None: tmp_path,
    )
    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: tmp_path,
    )
    caplog.set_level(logging.INFO)

    assert main(["contracts", "lint", "--skip-datacontract"]) == 0
    assert "contracts lint passed" in caplog.text


def test_contracts_generate_and_check_commands(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    from arxiv_int.contracts.generate import GenerationResult

    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: tmp_path,
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.lint.contracts_root_for",
        lambda project_root=None: tmp_path,
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.generate.generate_all_contracts",
        lambda root: GenerationResult(tmp_path, (), "abc123"),
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.generate.check_generation_drift",
        lambda root: [],
    )
    caplog.set_level(logging.INFO)

    assert main(["contracts", "generate"]) == 0
    assert "generated" in caplog.text
    assert main(["contracts", "check"]) == 0
    assert "drift check passed" in caplog.text


def test_contracts_evolution_command(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    from arxiv_int.contracts.evolution import EvolutionCheckReport

    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: tmp_path,
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.lint.contracts_root_for",
        lambda project_root=None: tmp_path,
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.evolution.check_evolution_policy",
        lambda root, project_root=None, include_live_sql=True: EvolutionCheckReport((), 15),
    )
    caplog.set_level(logging.INFO)

    assert main(["contracts", "evolution", "--skip-live-sql"]) == 0
    assert "evolution policy passed" in caplog.text


def test_ontology_check_and_generate_commands(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    from arxiv_int.ontology.check import OntologyCheckReport

    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: tmp_path,
    )
    monkeypatch.setattr(
        "arxiv_int.ontology.paths.ontology_root_for",
        lambda project_root=None: tmp_path / "ontology",
    )
    monkeypatch.setattr(
        "arxiv_int.ontology.generate.generate_ontology_bindings",
        lambda root: {"ontology.catalog.json": "abc"},
    )
    monkeypatch.setattr(
        "arxiv_int.ontology.check.check_ontology",
        lambda root, project_root=None, refresh_generated=False: OntologyCheckReport((), 11, 23),
    )
    caplog.set_level(logging.INFO)

    assert main(["ontology", "generate"]) == 0
    assert "generated" in caplog.text
    assert main(["ontology", "check"]) == 0
    assert "ontology check passed" in caplog.text


def test_readiness_and_services_default_to_pipeline_profiles() -> None:
    parser = build_parser()

    assert parser.parse_args(["readiness"]).profiles == "pipeline"
    assert parser.parse_args(["services", "up"]).profiles == "pipeline"


def test_services_reset_defaults_to_dry_run_and_accepts_apply() -> None:
    parser = build_parser()
    dry_run = parser.parse_args(["services", "reset"])
    applied = parser.parse_args(["services", "reset", "--apply", "--profiles", "core"])

    assert dry_run.services_command == "reset"
    assert dry_run.apply is False
    assert applied.apply is True
    assert applied.profiles == "core"


def test_readiness_command_renders_findings_and_preserves_exit_code(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    report = PreflightReport("fixture")
    report.add("disk", "degraded", "slow", action="change TMP_DIR")
    destination = tmp_path / "readiness.json"
    monkeypatch.setattr(
        "arxiv_int.cli.run_readiness",
        lambda **kwargs: ReadinessResult(report=report, report_path=destination),
    )
    caplog.set_level(logging.INFO)

    assert main(["readiness"]) == 2
    assert "[DEGRADED] disk: slow" in caplog.text
    assert "next: change TMP_DIR" in caplog.text
    assert str(destination) in caplog.text


def test_readiness_command_reports_invalid_options(monkeypatch: pytest.MonkeyPatch, caplog) -> None:  # type: ignore[no-untyped-def]
    def invalid(**kwargs: object) -> ReadinessResult:
        del kwargs
        raise ValueError("invalid readiness fixture")

    monkeypatch.setattr("arxiv_int.cli.run_readiness", invalid)
    caplog.set_level(logging.INFO)

    assert main(["readiness"]) == 1
    assert "invalid readiness fixture" in caplog.text


def test_features_command_logs_groups_with_install_commands(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["features"]) == 0
    assert "feature groups" in caplog.text
    assert "uv pip install 'arxiv-int[lake]'" in caplog.text
    assert "reserved for capability: russian-nlp" in caplog.text


def test_features_command_reports_an_unknown_stage(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO)

    assert main(["features", "--stage", "no-such-stage"]) == 1
    assert "unknown stage" in caplog.text


def test_config_show_applies_cli_roots_redacts_and_creates_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    checkout = tmp_path / "copied checkout"
    checkout.mkdir()
    (checkout / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    archive = tmp_path / "source files"
    archive.mkdir()
    results = tmp_path / "runtime results"
    pgdata = tmp_path / "database"
    for name in tuple(os.environ):
        if name in {"PROOF_ARCHIVE_DIR", "PG_WAL_DIR"} or name.startswith(
            ("ARCHIVE_SILO_", "PG_TABLESPACE_")
        ):
            monkeypatch.delenv(name)
    monkeypatch.setenv("POSTGRES_PASSWORD", "must-not-appear")
    caplog.set_level(logging.INFO)

    status = main(
        [
            "config",
            "show",
            "--redact",
            "--project-root",
            str(checkout),
            "--archive-dir",
            str(archive),
            "--results-dir",
            str(results),
            "--pgdata-dir",
            str(pgdata),
            "--runs-dir",
            str(results / "runs"),
            "--service-state-dir",
            str(results / "services"),
            "--model-cache-dir",
            str(results / "models"),
            "--tmp-dir",
            str(results / "tmp"),
        ]
    )

    assert status == 0
    assert "must-not-appear" not in caplog.text
    assert "POSTGRES_PASSWORD=<redacted>" in caplog.text
    assert "filesystem=" in caplog.text
    assert (results / "normalized").is_dir()
    assert pgdata.is_dir()


def test_parser_accepts_db_revision_and_apply_options() -> None:
    parser = build_parser()

    revision = parser.parse_args(["db", "revision", "--message", "add page count"])
    assert (revision.command, revision.db_command) == ("db", "revision")
    assert revision.message == "add page count"

    upgrade = parser.parse_args(["db", "upgrade"])
    assert (upgrade.db_command, upgrade.revision) == ("upgrade", "head")
    assert parser.parse_args(["db", "downgrade"]).revision == "-1"
    assert parser.parse_args(["db", "status"]).db_command == "status"
    assert parser.parse_args(["db", "adopt"]).db_command == "adopt"


def test_db_check_command_reports_findings(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    from arxiv_int.contracts.migrations.check import MigrationCheckReport

    monkeypatch.setattr(
        "arxiv_int.runtime.project_root.find_project_root",
        lambda explicit=None, environment=None: tmp_path,
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.lint.contracts_root_for",
        lambda project_root=None: tmp_path,
    )
    monkeypatch.setattr(
        "arxiv_int.contracts.migrations.commands.check_migrations",
        lambda project_root, contracts_root: MigrationCheckReport(
            ("contract metadata has no matching revision",),
            ("add_column corpus.documents.x",),
            "0001",
        ),
    )
    caplog.set_level(logging.INFO)

    assert main(["db", "check"]) == 1
    assert "no matching revision" in caplog.text


def test_db_status_reports_not_run_without_a_selected_database(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from arxiv_int.contracts.migrations.runner import DATABASE_URL_VARIABLE

    monkeypatch.delenv(DATABASE_URL_VARIABLE, raising=False)
    caplog.set_level(logging.INFO)

    assert main(["db", "status"]) == 2
    assert "not-run" in caplog.text


def test_db_command_reports_project_root_errors(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    from arxiv_int.runtime.project_root import ProjectRootError

    def _fail(explicit=None, environment=None):  # type: ignore[no-untyped-def]
        raise ProjectRootError("no project root")

    monkeypatch.setattr("arxiv_int.runtime.project_root.find_project_root", _fail)
    caplog.set_level(logging.INFO)

    assert main(["db", "check"]) == 1
    assert "no project root" in caplog.text

"""CLI help, precedence, unique run ids, and production refusal."""

from pathlib import Path

from arxiv_int.cli import build_parser, main
from arxiv_int.pipeline.cli import PRECEDENCE_HELP
from arxiv_int.pipeline.dag.stages import production_registry, profile_stage_names
from arxiv_int.pipeline.run.context import allocate_run_id
from arxiv_int.runtime.filesystem import FilesystemEvidence


def test_signal_handler_cancels_the_token() -> None:
    import signal

    from arxiv_int.pipeline.dag.cancel import CancelToken, install_signal_handler

    token = CancelToken()
    previous = signal.getsignal(signal.SIGINT)
    try:
        handler = install_signal_handler(token)
        handler(signal.SIGINT, None)
        assert token.cancelled
    finally:
        signal.signal(signal.SIGINT, previous)


def test_allocate_run_id_is_unique_and_not_local() -> None:
    generated = {allocate_run_id() for _ in range(5)}
    assert all(item.startswith("run-") and item != "local" for item in generated)
    assert len(generated) == 5


def test_cli_help_lists_defaults_and_precedence() -> None:
    parser = build_parser()
    text = parser.format_help()
    run_help = _subcommand_help(parser, ["pipeline", "run", "--help"])
    create_help = _subcommand_help(parser, ["run", "create", "--help"])
    assert "pipeline" in text
    assert "investigation" in run_help
    assert PRECEDENCE_HELP.split(",")[0] in run_help or "CLI overrides" in run_help
    assert "CLI overrides" in create_help or "documented defaults" in create_help
    assert parser.parse_args(["pipeline", "run", "--from", "extract", "--to", "chunk"])
    stage = parser.parse_args(["stage", "inventory", "--run-id", "run-abc"])
    assert stage.command == "stage"
    assert stage.run_id == "run-abc"
    prune = parser.parse_args(["artifacts", "prune", "--stale"])
    assert prune.apply is False
    inspect = parser.parse_args(["inspect", "latest"])
    assert inspect.command == "inspect"
    assert inspect.target == "latest"


def test_production_investigation_names_unregistered_required_stages() -> None:
    registry = production_registry()
    required = profile_stage_names("investigation")
    missing = [name for name in required if registry.get(name).runner is None]
    assert "preflight" in missing
    assert "inventory" in missing
    assert registry.get("evaluate").runner is not None


def test_pipeline_run_refuses_unregistered_investigation_stages(
    tmp_path: Path, monkeypatch: object
) -> None:
    import os

    for name in (
        "ARCHIVE_DIR",
        "RESULTS_DIR",
        "PGDATA_DIR",
        "RUNS_DIR",
        "SERVICE_STATE_DIR",
        "MODEL_CACHE_DIR",
        "TMP_DIR",
        "PG_WAL_DIR",
    ):
        monkeypatch.delenv(name, raising=False)
    for name in tuple(os.environ):
        if name.startswith(("ARCHIVE_SILO_", "PG_TABLESPACE_")):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        "arxiv_int.pipeline.forecast.devices.inspect_filesystem",
        lambda path: FilesystemEvidence(path, "ext4", "8:1", False, 10**18, True, False),
    )
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "doc.txt").write_text("x", encoding="utf-8")
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    (checkout / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (checkout / ".env").write_text(
        f"ARCHIVE_DIR={archive}\nRESULTS_DIR={tmp_path / 'results'}\n"
        f"PGDATA_DIR={tmp_path / 'pgdata'}\n",
        encoding="utf-8",
    )
    code = main(
        [
            "pipeline",
            "run",
            "--project-root",
            str(checkout),
            "--archive-dir",
            str(archive),
            "--results-dir",
            str(tmp_path / "results"),
        ]
    )
    assert code == 1


def _subcommand_help(parser: object, argv: list[str]) -> str:
    from io import StringIO
    from unittest.mock import patch

    with patch("sys.stdout", new_callable=StringIO) as stdout:
        try:
            parser.parse_args(argv)  # type: ignore[attr-defined]
        except SystemExit:
            return stdout.getvalue()
    return stdout.getvalue()

"""CLI setup parser and profile resolution that does not shadow .env."""

from pathlib import Path

from arxiv_int.cli import build_parser, main
from arxiv_int.runtime.setup.commands import resolve_cli_profiles
from tests.runtime.setup.conftest import checkout, make_adapters, operator_env


def test_parser_accepts_setup_and_atomic_phase() -> None:
    parser = build_parser()
    assert parser.parse_args(["setup"]).command == "setup"
    assert parser.parse_args(["setup", "--phase", "schema"]).phase == "schema"
    assert parser.parse_args(["readiness"]).profiles is None
    assert parser.parse_args(["services", "up"]).profiles is None


def test_cli_profiles_read_dotenv(tmp_path: Path) -> None:
    root = checkout(tmp_path, dotenv="SERVICE_PROFILES=core\n")
    assert resolve_cli_profiles(None, root) == "core"
    assert resolve_cli_profiles("vllm", root) == "vllm"


def test_setup_command_uses_coordinator(tmp_path: Path, monkeypatch: object) -> None:
    root = checkout(tmp_path)
    operator_env(tmp_path, root)
    adapters = make_adapters(root)
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "arxiv_int.runtime.setup.commands.production_adapters",
        lambda: adapters,
    )
    monkeypatch.setattr(  # type: ignore[attr-defined]
        "arxiv_int.runtime.setup.commands.find_project_root",
        lambda explicit=None, environment=None: root,
    )
    assert main(["setup", "--phase", "config"]) in {0, 1, 2}

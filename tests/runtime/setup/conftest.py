"""Shared fakes for deterministic setup tests."""

from collections.abc import Callable, Mapping
from pathlib import Path
from subprocess import CompletedProcess

import pytest

from arxiv_int.contracts.migrations.runner import STATUS_OK, RunnerOutcome
from arxiv_int.readiness import CommandResult, HttpResult
from arxiv_int.runtime.setup.adapters import CancelToken, SetupAdapters
from arxiv_int.stores.postgres.apply import SchemaApplyReport

PROJECT_ROOT = Path(__file__).parents[3]
EXAMPLE_DOTENV = (
    "ARCHIVE_DIR=/path/to/archive\n"
    "RESULTS_DIR=/path/to/results\n"
    "PGDATA_DIR=/path/to/pgdata\n"
    "POSTGRES_PASSWORD=fixture-secret\n"
)


class FixtureProbe:
    def __init__(self, *, endpoint: bool = True, models: set[str] | None = None) -> None:
        self.endpoint = endpoint
        self.models = models or {"fixture-model"}

    def which(self, executable: str) -> str | None:
        return f"/usr/bin/{executable}"

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        environment: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CommandResult:
        del cwd, environment, timeout
        if "ps" in command and "--format" in command:
            return CommandResult(
                0,
                '[{"Service":"database","State":"running","Health":"healthy"},'
                '{"Service":"grafana","State":"running","Health":"healthy"},'
                '{"Service":"prometheus","State":"running","Health":"healthy"},'
                '{"Service":"postgres-exporter","State":"running","Health":"healthy"}]',
            )
        if "psql" in command:
            return CommandResult(0, "pg_search=0.25.6/0.25.6\nvector=0.8.0/0.8.0\n")
        return CommandResult(0, f"{command[0]} fixture")

    def get_json(self, url: str, *, timeout: float) -> HttpResult:
        del url, timeout
        if not self.endpoint:
            return HttpResult(None, error="ConnectionRefusedError")
        return HttpResult(200, {"models": [{"name": name} for name in sorted(self.models)]})

    def memory_bytes(self) -> int:
        return 128 * 1024**3


def completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> CompletedProcess[str]:
    return CompletedProcess((), returncode, stdout, stderr)


def checkout(tmp_path: Path, *, dotenv: str | None = EXAMPLE_DOTENV, example: bool = True) -> Path:
    root = tmp_path / "a checkout"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (root / "uv.lock").write_text("lock=1\n", encoding="utf-8")
    if example:
        (root / ".env.example").write_text(
            "# ARCHIVE_DIR=\n# RESULTS_DIR=\n# PGDATA_DIR=\n# POSTGRES_PASSWORD=\nDATA_DIR=.data\n",
            encoding="utf-8",
        )
    if dotenv is not None:
        (root / ".env").write_text(dotenv, encoding="utf-8")
    (root / "docker").symlink_to(PROJECT_ROOT / "docker", target_is_directory=True)
    return root


def operator_env(tmp_path: Path, root: Path, **overrides: str) -> dict[str, str]:
    archive = tmp_path / "archive"
    archive.mkdir(exist_ok=True)
    values = {
        "ARCHIVE_DIR": str(archive),
        "RESULTS_DIR": str(tmp_path / "results"),
        "PGDATA_DIR": str(tmp_path / "pgdata"),
        "DATA_DIR": str(tmp_path / "data"),
        "POSTGRES_PASSWORD": "fixture-secret",
        "GENERATION_MODEL": "fixture-model",
        "EMBEDDING_MODEL": "fixture-model",
        **overrides,
    }
    (root / ".env").write_text(
        "\n".join(f"{name}={value}" for name, value in values.items()) + "\n",
        encoding="utf-8",
    )
    return values


def _fake_runner(sync_ok: bool) -> Callable[..., CompletedProcess[str]]:
    def runner(
        command: tuple[str, ...], *, cwd: Path, env: Mapping[str, str] | None = None
    ) -> CompletedProcess[str]:
        del env
        if command[:2] == ("uv", "sync"):
            if not sync_ok:
                return completed(1, stderr="sync failed")
            executable = cwd / ".venv" / "bin" / "arxiv-int"
            executable.parent.mkdir(parents=True, exist_ok=True)
            executable.write_text("#!/bin/sh\n", encoding="utf-8")
            executable.chmod(0o755)
            return completed(0)
        if command == ("tesseract", "--list-langs"):
            return completed(0, stdout="List of available languages:\ndeu\neng\nosd\nrus\nukr\n")
        if "info" in command:
            return completed(0, stdout="arxiv-int 0.1.0 (arxiv_int)")
        if command[:1] == ("ollama",):
            return completed(0, stdout="NAME\nfixture-model\n")
        return completed(0)

    return runner


def make_adapters(
    root: Path,
    *,
    probe: FixtureProbe | None = None,
    listed_models: set[str] | None = None,
    image_present: bool = True,
    sync_ok: bool = True,
    compose_ok: bool = True,
    wait_seconds: float = 0.01,
) -> SetupAdapters:
    del root
    images = (
        {"grafana": "grafana/grafana:fixture"}
        if image_present
        else {"grafana": "missing/image:tag"}
    )
    return SetupAdapters(
        which=lambda name: f"/usr/bin/{name}",
        run=_fake_runner(sync_ok),
        probe=probe or FixtureProbe(models=listed_models or {"fixture-model"}),
        compose=lambda *_args, **_kwargs: 0 if compose_ok else 1,
        image_present=lambda _ref: image_present,
        build_image=lambda _root: 0,
        listed_images=images,
        listed_models=listed_models if listed_models is not None else {"fixture-model"},
        sleep=lambda _seconds: None,
        cancel=CancelToken(),
        wait_seconds=wait_seconds,
    )


@pytest.fixture(autouse=True)
def _fake_schema_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.inspect_and_compare",
        lambda _root, _url, **_kwargs: ([], {"schemas": []}, None),
    )
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.apply_revisions",
        lambda *_args, **_kwargs: SchemaApplyReport(
            RunnerOutcome(STATUS_OK, "applied"), (), Path("ev.json"), "0001", {}
        ),
    )

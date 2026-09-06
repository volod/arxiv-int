import json
from collections.abc import Mapping
from pathlib import Path

from arxiv_int.readiness import CommandResult, HttpResult
from arxiv_int.readiness.run import run_readiness
from arxiv_int.runtime import FilesystemEvidence


class FixtureProbe:
    def __init__(
        self,
        *,
        database: bool = True,
        endpoint: bool = True,
        missing_tool: str | None = None,
        timeout_tool: str | None = None,
    ) -> None:
        self.database, self.endpoint = database, endpoint
        self.missing_tool, self.timeout_tool = missing_tool, timeout_tool
        self.environments: list[Mapping[str, str]] = []

    def which(self, executable: str) -> str | None:
        if executable == self.missing_tool:
            return None
        return f"/usr/bin/{executable}"

    def run(
        self,
        command: tuple[str, ...],
        *,
        cwd: Path,
        environment: Mapping[str, str] | None = None,
        timeout: float,
    ) -> CommandResult:
        del cwd, timeout
        if environment is not None:
            self.environments.append(environment)
        if command[0] == self.timeout_tool:
            return CommandResult(124, timed_out=True)
        if "ps" in command and "--format" in command:
            services = ("database", "grafana", "postgres-exporter", "prometheus")
            state = json.dumps(
                [dict(Service=name, State="running", Health="healthy") for name in services]
                if self.database
                else []
            )
            return CommandResult(0, state)
        if "psql" in command:
            return CommandResult(0, "pg_search=0.25.6/0.25.6\nvector=0.8.0/0.8.0\n")
        return CommandResult(0, f"{command[0]} fixture-version")

    def get_json(self, url: str, *, timeout: float) -> HttpResult:
        del url, timeout
        if not self.endpoint:
            return HttpResult(None, error="ConnectionRefusedError")
        return HttpResult(200, {"models": [{"name": "fixture-model"}]})

    def memory_bytes(self) -> int:
        return 128 * 1024**3


def _project(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    archive = tmp_path / "archive"
    archive.mkdir()
    return root, {
        "ARCHIVE_DIR": str(archive),
        "RESULTS_DIR": str(tmp_path / "results"),
        "PGDATA_DIR": str(tmp_path / "pgdata"),
        "POSTGRES_PASSWORD": "never-render-this-secret",
        "EMBEDDING_MODEL": "fixture-model",
        "GENERATION_MODEL": "fixture-model",
    }


def _evidence(
    path: Path,
    *,
    filesystem: str = "ext4",
    rotational: bool = False,
    ownership: bool = True,
) -> FilesystemEvidence:
    return FilesystemEvidence(
        path=path,
        filesystem=filesystem,
        device_id="8:1",
        rotational=rotational,
        free_bytes=100 * 1024**3,
        ownership_capable=ownership,
        read_only=False,
    )


def test_ready_readiness_persists_redacted_json_under_results(tmp_path: Path) -> None:
    root, environment = _project(tmp_path)
    probe = FixtureProbe()

    result = run_readiness(
        project_root=root,
        environment=environment,
        probe=probe,
        inspector=_evidence,
    )

    assert result.report.status == "ready"
    assert result.report.exit_code == 0
    assert result.report_path == tmp_path / "results/reports/readiness.json"
    payload = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert payload["status"] == "ready"
    assert "never-render-this-secret" not in result.report_path.read_text(encoding="utf-8")
    assert result.report_path.stat().st_mode & 0o777 == 0o600
    assert all(
        env["POSTGRES_PASSWORD"] == environment["POSTGRES_PASSWORD"] for env in probe.environments
    )
    path_detail = next(
        item["detail"] for item in payload["findings"] if item["name"] == "path.PGDATA_DIR"
    )
    assert all(
        evidence in path_detail
        for evidence in ("class=database", "filesystem=ext4", "device=8:1", "rotational=false")
    )

    rerun = run_readiness(
        project_root=root,
        environment=environment,
        probe=probe,
        inspector=_evidence,
    )
    assert rerun.report.status == "ready"
    assert rerun.report_path == result.report_path


def test_degraded_readiness_accumulates_storage_services_and_endpoint(tmp_path: Path) -> None:
    root, environment = _project(tmp_path)
    probe = FixtureProbe(database=False, endpoint=False)

    result = run_readiness(
        project_root=root,
        environment=environment,
        persist=False,
        probe=probe,
        inspector=lambda path: _evidence(path, rotational=True),
    )

    assert result.report.status == "degraded"
    assert result.report.exit_code == 2
    details = "\n".join(item.detail for item in result.report.findings)
    assert all(
        item.status == "ready" for item in result.report.findings if item.name.startswith("path.")
    )
    assert "state=absent" in details
    assert "local API is unavailable" in details
    assert any(item.action == "make services-up" for item in result.report.findings)


def test_blocked_readiness_masks_secret_and_reports_every_failure(tmp_path: Path) -> None:
    root, environment = _project(tmp_path)
    environment["POSTGRES_PASSWORD"] = "replace-me"
    probe = FixtureProbe(missing_tool="uv", timeout_tool="docker")
    pgdata = Path(environment["PGDATA_DIR"])

    def inspect(path: Path) -> FilesystemEvidence:
        if path == pgdata:
            return _evidence(path, filesystem="nfs", ownership=False)
        return _evidence(path)

    result = run_readiness(
        project_root=root,
        environment=environment,
        persist=False,
        probe=probe,
        inspector=inspect,
    )

    assert result.report.status == "blocked"
    assert result.report.exit_code == 1
    rendered = "\n".join(result.report.console_lines())
    assert "uv is not installed" in rendered
    assert "probe timed out" in rendered
    assert "change PGDATA_DIR" in rendered
    assert "replace-me" not in rendered


def test_report_path_must_stay_under_results(tmp_path: Path) -> None:
    root, environment = _project(tmp_path)
    outside = tmp_path / "outside.json"

    result = run_readiness(
        project_root=root,
        environment=environment,
        report_path=outside,
        probe=FixtureProbe(),
        inspector=_evidence,
    )

    assert result.report.status == "blocked"
    assert result.report_path is None
    assert not outside.exists()
    assert any(item.name == "report.json" for item in result.report.findings)


def test_missing_configuration_still_returns_tool_and_resource_findings(tmp_path: Path) -> None:
    root = tmp_path / "checkout"
    root.mkdir()
    (root / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")

    result = run_readiness(project_root=root, environment={}, probe=FixtureProbe())

    assert result.report.status == "blocked"
    names = {item.name for item in result.report.findings}
    assert {"tool.python", "resource.ram", "config.runtime"} <= names
    assert result.report_path is None


def test_remote_inference_endpoint_is_blocked_without_a_request(tmp_path: Path) -> None:
    root, environment = _project(tmp_path)
    environment["OLLAMA_BASE_URL"] = "https://models.example.test"

    result = run_readiness(
        project_root=root,
        environment=environment,
        persist=False,
        probe=FixtureProbe(),
        inspector=_evidence,
    )

    assert result.report.status == "blocked"
    assert any(
        item.name == "inference.endpoint" and "not a loopback" in item.detail
        for item in result.report.findings
    )


def test_vllm_profile_blocks_without_an_nvidia_runtime(tmp_path: Path) -> None:
    root, environment = _project(tmp_path)
    environment["INFERENCE_BACKEND"] = "vllm"

    result = run_readiness(
        project_root=root,
        environment=environment,
        profiles="vllm",
        persist=False,
        probe=FixtureProbe(missing_tool="nvidia-smi"),
        inspector=_evidence,
    )

    gpu = next(item for item in result.report.findings if item.name == "resource.gpu")
    assert gpu.status == "blocked"
    assert "NVIDIA" in gpu.detail

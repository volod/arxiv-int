from pathlib import Path

import pytest
from test_workstation import FixtureProbe, _evidence, _project

from arxiv_int.readiness import HttpResult
from arxiv_int.readiness.run import run_readiness
from arxiv_int.runtime import FilesystemEvidence


class ServiceProbe(FixtureProbe):
    def __init__(self) -> None:
        super().__init__()
        self.urls: list[str] = []

    def get_json(self, url: str, *, timeout: float) -> HttpResult:
        self.urls.append(url)
        return HttpResult(200, {"data": [{"id": "service-model"}]})


@pytest.mark.parametrize("profiles", ["core", "vllm", "core vllm", "cadvisor"])
def test_readiness_checks_only_selected_services_and_disks(tmp_path: Path, profiles: str) -> None:
    root, environment = _project(tmp_path)
    environment.update(
        ARCHIVE_DIR=str(tmp_path / "missing"), VLLM_MODEL="service-model", VLLM_PORT="8100"
    )
    if "core" not in profiles:
        environment["POSTGRES_PASSWORD"] = ""
    probe = ServiceProbe()
    inspected: list[Path] = []

    def inspect(path: Path) -> FilesystemEvidence:
        inspected.append(path)
        assert path != Path(environment["ARCHIVE_DIR"])
        if "core" not in profiles:
            assert path != Path(environment["PGDATA_DIR"])
        return _evidence(path)

    result = run_readiness(
        project_root=root,
        environment=environment,
        profiles=profiles,
        probe=probe,
        inspector=inspect,
        persist=False,
    )
    names = {item.name for item in result.report.findings}
    assert ("config.POSTGRES_PASSWORD" in names) == ("core" in profiles)
    assert ("database.extensions" in names) == ("core" in profiles)
    assert ("service.database" in names) == ("core" in profiles)
    assert ("inference.models" in names) == ("vllm" in profiles)
    assert not {"service.grafana", "service.prometheus", "path.SERVICE_STATE_DIR"} & names
    assert not any(item.status == "blocked" for item in result.report.findings)
    assert probe.urls == (["http://127.0.0.1:8100/v1/models"] if "vllm" in profiles else [])

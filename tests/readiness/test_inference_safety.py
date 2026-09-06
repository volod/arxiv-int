"""Inference safety at the injected probe boundary."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from test_workstation import _project

from arxiv_int.readiness import HttpResult, PreflightReport
from arxiv_int.readiness.inference import check_inference
from arxiv_int.runtime import load_runtime_config


@pytest.mark.parametrize("payload", [None, [], {}, {"models": [1]}, {"models": [{"name": 12}]}])
def test_malformed_model_payload_is_not_ready(tmp_path: Path, payload: object) -> None:
    root, environment = _project(tmp_path)
    config = load_runtime_config(project_root=root, environment=environment)
    probe = MagicMock()
    probe.get_json.return_value = HttpResult(200, payload)
    report = PreflightReport("inference")
    check_inference(report, config, probe, 1)
    assert report.status == "degraded"
    assert report.findings[0].name == "inference.endpoint"


def test_credential_url_is_refused_before_injected_transport(tmp_path: Path) -> None:
    root, environment = _project(tmp_path)
    environment["OLLAMA_BASE_URL"] = "http://user:fixture-secret@localhost:11434"
    config = load_runtime_config(project_root=root, environment=environment)
    probe = MagicMock()
    report = PreflightReport("inference")
    check_inference(report, config, probe, 1)
    assert report.status == "blocked"
    assert "fixture-secret" not in str(report.as_dict())
    probe.get_json.assert_not_called()

"""Configured-service schema binding without a disposable fallback."""

from pathlib import Path

import pytest

from arxiv_int.contracts.migrations.runner import STATUS_OK, RunnerOutcome
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.setup.schema import bound_service_url, run_schema_phase, service_database_url
from arxiv_int.stores.postgres.apply import SchemaApplyReport
from tests.runtime.setup.conftest import checkout, operator_env


def _config(tmp_path: Path):
    root = checkout(tmp_path)
    environment = operator_env(tmp_path, root)
    return load_runtime_config(project_root=root, environment=environment)


def test_service_url_uses_loopback_and_redacts_conflicts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    url = service_database_url(config)
    assert "127.0.0.1" in url
    assert "fixture-secret" in url
    matching = bound_service_url(config, url)
    assert matching == url
    with pytest.raises(ValueError, match="does not match"):
        bound_service_url(config, "postgresql+psycopg://arxiv_int:x@127.0.0.1:1/scratch")


def test_schema_phase_refuses_drift_and_never_calls_disposable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)
    calls: list[str] = []

    def inspect(
        _root: Path, url: str, **_kwargs: object
    ) -> tuple[list[str], dict[str, object], str]:
        calls.append(url)
        return (
            ["drift"],
            {"schemas": ["ctl", "corpus", "search", "knowledge", "ontology", "eval"]},
            "0001",
        )

    monkeypatch.setattr("arxiv_int.runtime.setup.schema.inspect_and_compare", inspect)
    monkeypatch.setattr(
        "arxiv_int.runtime.setup.schema.apply_revisions",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("apply")),
    )
    monkeypatch.setattr(
        "arxiv_int.stores.postgres.apply.apply_on_disposable",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("disposable")),
    )
    result = run_schema_phase(config, override=None, run_id="t")
    assert result.status == "blocked"
    assert "drift" in result.detail
    assert "adopt" in (result.action or "")
    assert calls and "127.0.0.1" in calls[0]


def test_schema_phase_applies_empty_service_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    config = _config(tmp_path)

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
    result = run_schema_phase(config, override=None, run_id="t")
    assert result.status == "ready"
    assert "0001" in result.detail

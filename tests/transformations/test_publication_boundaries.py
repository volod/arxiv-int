"""Publication must depend on current evidence and preserve active data."""

import json
from pathlib import Path

import pytest

from arxiv_int.transformations import runner
from arxiv_int.transformations.activation import load_active_generation
from arxiv_int.transformations.invoke import InvokeOutcome
from arxiv_int.transformations.model import TransformRequest

ROOT = Path(__file__).parents[2]
URL = "postgresql://fixture:synthetic-secret@127.0.0.1/fixture"


@pytest.mark.parametrize("stale", [False, True])
def test_success_without_current_evidence_cannot_activate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, stale: bool
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    target = tmp_path / "dbt" / "missing" / "target"
    target.mkdir(parents=True)
    if stale:
        (target / "run_results.json").write_text(
            json.dumps({"results": [{"unique_id": "test.old", "status": "pass"}]})
        )
    monkeypatch.setattr(runner, "invoke_dbt", lambda *args: InvokeOutcome(True, "ok"))
    monkeypatch.setattr(runner, "_row_counts", lambda url, names: dict.fromkeys(names, 1))
    result = runner.run_transform(
        TransformRequest(
            command="build", run_id="missing", project_root=ROOT, database_url=URL, activate=True
        )
    )
    assert not result.activatable
    assert load_active_generation(ROOT) is None


def test_failure_detail_does_not_retain_database_password(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        runner,
        "invoke_dbt",
        lambda *args: InvokeOutcome(False, "connection failed for synthetic-secret"),
    )
    result = runner.run_transform(
        TransformRequest(command="build", run_id="secret", project_root=ROOT, database_url=URL)
    )
    assert "synthetic-secret" not in result.detail
    assert "synthetic-secret" not in (Path(result.artifact_dir) / "result.json").read_text()


def test_missing_database_retry_preserves_prior_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.delenv("ARXIV_INT_TRANSFORM_DATABASE_URL", raising=False)
    monkeypatch.delenv("ARXIV_INT_MIGRATION_DATABASE_URL", raising=False)
    artifact_dir = tmp_path / "dbt" / "published"
    artifact_dir.mkdir(parents=True)
    evidence = artifact_dir / "result.json"
    evidence.write_text('{"status": "ok", "activatable": true}')
    previous = evidence.read_bytes()
    result = runner.run_transform(
        TransformRequest(command="build", run_id="published", project_root=ROOT)
    )
    assert result.status == "not-run"
    assert evidence.read_bytes() == previous
    assert Path(result.artifact_dir) != artifact_dir

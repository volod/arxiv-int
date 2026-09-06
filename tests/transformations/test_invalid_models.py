from pathlib import Path

import pytest

from arxiv_int.features.guard import module_available
from arxiv_int.quality.project_root import discover_project_root
from arxiv_int.transformations.model import STATUS_FAILED, TransformRequest
from arxiv_int.transformations.runner import run_transform


def test_invalid_model_fails_parse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    if not module_available("dbt.cli.main") or not module_available("dbt.adapters.postgres"):
        pytest.skip("transform extra is not installed")
    root = discover_project_root(Path(__file__))
    import shutil

    shutil.copytree(root / "transformations", tmp_path / "transformations")
    generated = tmp_path / "contracts" / "generated" / "dbt"
    generated.mkdir(parents=True)
    shutil.copy(root / "contracts" / "generated" / "dbt" / "sources.yml", generated / "sources.yml")
    broken = tmp_path / "transformations" / "models" / "staging" / "stg_documents.sql"
    broken.write_text("select 1 from {{ ref('missing_model_xyz') }}\n", encoding="utf-8")
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    result = run_transform(
        TransformRequest(command="parse", run_id="invalid-sql", project_root=tmp_path)
    )
    assert result.status == STATUS_FAILED
    assert result.activatable is False
    assert "secret" not in result.detail.lower() or "super-secret" not in result.detail

"""Real run-context creation with isolated operator roots."""

from pathlib import Path

import pytest

from arxiv_int.pipeline.commands import create_run_context
from arxiv_int.pipeline.run.context import RunContext


@pytest.fixture
def frozen_run(tmp_path: Path) -> RunContext:
    archive = tmp_path / "archive"
    archive.mkdir()
    (archive / "doc.txt").write_text("one", encoding="utf-8")
    project = tmp_path / "project"
    project.mkdir()
    (project / "pyproject.toml").write_text("[project]\nname='fixture'\n", encoding="utf-8")
    (project / ".env").write_text(
        f"ARCHIVE_DIR={archive}\nRESULTS_DIR={tmp_path / 'results'}\n"
        f"PGDATA_DIR={tmp_path / 'pgdata'}\n",
        encoding="utf-8",
    )
    return create_run_context(project_root=project, environment={})

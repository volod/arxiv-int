"""Atomic commands enforce the frozen source guard without rereading source bytes."""

import argparse
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from arxiv_int.pipeline.dag.dispatch import run_pipeline_command
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import RunStatus, save_status


def _arguments(context: RunContext, action: str) -> argparse.Namespace:
    return argparse.Namespace(
        command="stage" if action == "stage" else "run",
        run_command=action,
        run_id=context.run_id,
        runs_dir=context.runs_dir,
        project_root=context.project_root,
        force=False,
        stage="preflight",
        document_id=None,
    )


@pytest.mark.parametrize("action", ["stage", "status", "resume"])
def test_command_refuses_changed_archive(frozen_run: RunContext, action: str) -> None:
    save_status(
        frozen_run.runs_dir,
        RunStatus(frozen_run.run_id, frozen_run.generation_id, False, "", (), (), ()),
    )
    (frozen_run.silos[0].root / "doc.txt").write_bytes(b"changed")
    with (
        patch.dict(os.environ, {}, clear=True),
        patch("arxiv_int.pipeline.dag.dispatch.run_dag") as worker,
    ):
        assert run_pipeline_command(_arguments(frozen_run, action)) != 0
        worker.assert_not_called()


@pytest.mark.parametrize("action", ["stage", "status", "resume"])
def test_unchanged_command_never_opens_source_bytes(frozen_run: RunContext, action: str) -> None:
    save_status(
        frozen_run.runs_dir,
        RunStatus(frozen_run.run_id, frozen_run.generation_id, False, "", (), (), ()),
    )
    original_open = Path.open

    def guard(path: Path, *args: object, **kwargs: object) -> object:
        assert not path.is_relative_to(frozen_run.silos[0].root)
        return original_open(path, *args, **kwargs)

    with (
        patch.dict(os.environ, {}, clear=True),
        patch.object(Path, "open", guard),
        patch("arxiv_int.pipeline.dag.dispatch.run_dag", return_value=0),
    ):
        assert run_pipeline_command(_arguments(frozen_run, action)) == 0

"""Stage-boundary recheck checkpoints before allocation."""

from pathlib import Path

import pytest

from arxiv_int.pipeline.dag.actions import fixture_plan
from arxiv_int.pipeline.dag.orchestrate import Orchestrator
from arxiv_int.pipeline.forecast.errors import ForecastRefusedError
from arxiv_int.pipeline.forecast.model import (
    ByteRange,
    DeviceBudget,
    ForecastDocument,
    HostAssumptions,
)
from arxiv_int.pipeline.forecast.recheck import make_space_guard, recheck_free_space
from arxiv_int.pipeline.run.fixtures import (
    FIXTURE_OPTIONAL,
    FIXTURE_PROFILE_STAGES,
    fixture_registry,
)
from arxiv_int.runtime.filesystem import FilesystemEvidence
from tests.pipeline.conftest import make_context


def _plan(registry):
    return fixture_plan(
        registry, profile_stages=FIXTURE_PROFILE_STAGES, optional_stages=FIXTURE_OPTIONAL
    )


def _document(path: Path, *, free_ok: bool) -> ForecastDocument:
    from arxiv_int.pipeline.forecast.model import SCHEMA_ID, OutputCosts, TimeRange

    peak = ByteRange(100, 500)
    device = DeviceBudget(
        "8:1",
        ("RESULTS_DIR", "RUNS_DIR"),
        str(path),
        "ext4",
        ("bulk",),
        False,
        10**12 if free_ok else 0,
        True,
        peak,
        1_000,
        "ready" if free_ok else "blocked",
        (),
    )
    zeros = ByteRange(0, 0)
    outputs = OutputCosts(
        zeros, zeros, zeros, zeros, zeros, zeros, zeros, zeros, zeros, zeros, zeros, zeros, zeros
    )
    return ForecastDocument(
        SCHEMA_ID,
        "forecast-test",
        "run-test",
        True,
        "fixture",
        ("alpha", "beta", "gamma"),
        ("omega",),
        "ready",
        "low",
        "fp",
        "cfg",
        "snap",
        "env",
        "sample",
        (),
        (device,),
        outputs,
        TimeRange(1.0, 2.0),
        ("alpha", "beta", "gamma"),
        HostAssumptions(16.0, "none", 0.0, "cpu", 1),
        (),
        (),
        ("archive-organization",),
    )


def test_simulated_free_space_loss_halts_before_allocation(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)
    lost = tmp_path / "full-disk"
    lost.mkdir()
    document = _document(lost, free_ok=True)

    def inspector(path: Path) -> FilesystemEvidence:
        del path
        return FilesystemEvidence(lost, "ext4", "8:1", False, 0, True, False)

    orchestrator = Orchestrator(
        registry, context.runs_dir, space_guard=make_space_guard(document, inspector)
    )
    status = orchestrator.execute_plan(context, _plan(registry))
    assert status.halted
    assert "below peak" in status.halt_reason
    assert status.executions == ()
    assert runners["alpha"].calls == 0
    assert not list((context.runs_dir / context.run_id / "manifests").glob("**/*"))


def test_space_guard_allows_work_when_headroom_remains(tmp_path: Path) -> None:
    registry, runners = fixture_registry()
    context = make_context(tmp_path)
    target = tmp_path / "wide-disk"
    target.mkdir()
    document = _document(target, free_ok=True)

    def inspector(path: Path) -> FilesystemEvidence:
        del path
        return FilesystemEvidence(target, "ext4", "8:1", False, 10**12, True, False)

    status = Orchestrator(
        registry, context.runs_dir, space_guard=make_space_guard(document, inspector)
    ).execute_plan(context, _plan(registry))
    assert not status.halted
    assert runners["alpha"].calls == 1
    assert runners["gamma"].calls == 1


def test_recheck_raises_forecast_refused_without_partial_stage() -> None:
    document = _document(Path("/unused"), free_ok=True)

    def inspector(path: Path) -> FilesystemEvidence:
        return FilesystemEvidence(path, "ext4", "8:1", False, 0, True, False)

    with pytest.raises(ForecastRefusedError, match="below peak"):
        recheck_free_space(document, inspector, "alpha")

"""Registered evaluate stage that publishes an immutable evaluation bundle."""

from pathlib import Path

from arxiv_int.evaluation.eval_paths import fixture_root
from arxiv_int.evaluation.evaluate_run import EvaluateRequest, run_evaluate
from arxiv_int.evaluation.fixture_kinds import DEFAULT_BOOTSTRAP_SEED
from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.runtime.project_root import find_project_root


class EvaluateStage:
    """Fixture-backed evaluate runner used by CLI, Make, and later DAG wiring."""

    stage = "evaluate"
    feature = "evaluation"
    depends_on: tuple[str, ...] = ()

    def run(self, context: StageContext) -> StageResult:
        """Score frozen fixtures and write ``$RUNS_DIR/<run-id>/evaluation``."""
        project_root = _project_root(context)
        request = EvaluateRequest(
            run_id=context.run_id,
            project_root=project_root,
            fixture_root=_option_path(context, "fixture_root", fixture_root(project_root)),
            runs_dir=_option_path(context, "runs_dir", context.results_dir),
            seed=int(context.options.get("seed") or DEFAULT_BOOTSTRAP_SEED),
        )
        outcome = run_evaluate(request)
        return StageResult(
            stage=self.stage,
            outcome="produced",
            detail=f"published evaluation bundle fingerprint={outcome.bundle.fingerprint}",
        )


def _project_root(context: StageContext) -> Path:
    raw = context.options.get("project_root")
    if raw:
        return Path(raw)
    return find_project_root()


def _option_path(context: StageContext, name: str, default: Path) -> Path:
    raw = context.options.get(name)
    return Path(raw) if raw else default

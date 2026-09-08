"""In-process fixture stage runners used by DAG tests and CLI fixtures."""

from collections.abc import Callable
from dataclasses import replace

from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.interfaces.stores import DatasetRef
from arxiv_int.pipeline.dag.registry import ResourceEstimate, StageRegistry, StageSpec

FixtureHook = Callable[[StageContext], None]


class FixtureStage:
    """Record invocations and emit a deterministic dataset ref or a failed outcome."""

    def __init__(
        self,
        name: str,
        *,
        feature: str = "lake",
        fail: bool = False,
        outcome: str = "produced",
        hook: FixtureHook | None = None,
    ) -> None:
        self.stage = name
        self.feature = feature
        self.depends_on: tuple[str, ...] = ()
        self.calls = 0
        self._outcome = "failed" if fail else outcome
        self._hook = hook

    def run(self, context: StageContext) -> StageResult:
        """Produce one logical output or report an injected failure."""
        self.calls += 1
        if self._hook is not None:
            self._hook(context)
        if self._outcome == "failed":
            return StageResult(self.stage, "failed", "injected fixture failure")
        if self._outcome == "empty":
            return StageResult(self.stage, "empty", "fixture empty")
        output = DatasetRef(self.stage, "1.0.0", context.generation_id, {"shard": "default"})
        if self._outcome == "partial":
            return StageResult(self.stage, "partial", "fixture partial", outputs=(output,))
        return StageResult(self.stage, "produced", "fixture produced", outputs=(output,))


def fixture_specs(
    *,
    fail_gamma: bool = False,
    gamma_hook: FixtureHook | None = None,
    gamma_outcome: str = "produced",
    validators: tuple[str, ...] = (),
    dbt_select: tuple[str, ...] = (),
) -> tuple[tuple[StageSpec, ...], dict[str, FixtureStage]]:
    """Return the alpha/beta/gamma/omega fixture DAG and its runners."""
    runners = {
        "alpha": FixtureStage("alpha"),
        "beta": FixtureStage("beta"),
        "gamma": FixtureStage("gamma", fail=fail_gamma, outcome=gamma_outcome, hook=gamma_hook),
        "omega": FixtureStage("omega"),
    }
    estimate = ResourceEstimate()
    specs: tuple[StageSpec, ...] = (
        StageSpec("alpha", "1", (), (), (), estimate, (), (), runners["alpha"]),
        StageSpec(
            "beta", "1", ("alpha",), ("alpha",), (), estimate, validators, (), runners["beta"]
        ),
        StageSpec(
            "gamma",
            "1",
            ("beta",),
            ("beta",),
            (),
            estimate,
            (),
            dbt_select,
            runners["gamma"],
        ),
        StageSpec("omega", "1", ("beta",), ("beta",), (), estimate, (), (), runners["omega"], True),
    )
    specs = tuple(
        replace(
            spec,
            tools={
                "fixture-runner": "FixtureStage",
                "feature": runners[spec.name].feature,
                "outcome": runners[spec.name]._outcome,
            },
        )
        for spec in specs
    )
    return specs, runners


def fixture_registry(**kwargs: object) -> tuple[StageRegistry, dict[str, FixtureStage]]:
    """Build the fixture registry used by orchestration tests."""
    specs, runners = fixture_specs(**kwargs)  # type: ignore[arg-type]
    return StageRegistry(specs), runners


FIXTURE_PROFILE_STAGES: tuple[str, ...] = ("alpha", "beta", "gamma")
FIXTURE_OPTIONAL: frozenset[str] = frozenset({"omega"})

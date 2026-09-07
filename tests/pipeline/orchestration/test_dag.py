"""DAG planning: order, range, skip sets, and invalid dependencies."""

import pytest

from arxiv_int.pipeline.errors import CyclicDependencyError, InvalidRangeError, UnknownStageError
from arxiv_int.pipeline.fixtures import FIXTURE_OPTIONAL, FIXTURE_PROFILE_STAGES, fixture_registry
from arxiv_int.pipeline.graph import select_plan, topological_order
from arxiv_int.pipeline.registry import ResourceEstimate, StageRegistry, StageSpec


def test_topological_order_is_stable_and_dependency_aware() -> None:
    registry, _runners = fixture_registry()
    order = topological_order(FIXTURE_PROFILE_STAGES, registry.dependencies())
    assert order == ("alpha", "beta", "gamma")


def test_full_plan_skips_optional_omega() -> None:
    registry, _runners = fixture_registry()
    plan = select_plan(
        registry.dependencies(),
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
    )
    assert plan.execute == ("alpha", "beta", "gamma")
    assert plan.assumed_upstream == ()
    assert plan.not_selected == ("omega",)


def test_to_range_is_the_endpoint_closure() -> None:
    registry, _runners = fixture_registry()
    plan = select_plan(
        registry.dependencies(),
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
        to_stage="beta",
    )
    assert plan.execute == ("alpha", "beta")


def test_from_range_requires_upstream_and_runs_descendants() -> None:
    registry, _runners = fixture_registry()
    plan = select_plan(
        registry.dependencies(),
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
        from_stage="beta",
        to_stage="gamma",
    )
    assert plan.execute == ("beta", "gamma")
    assert plan.assumed_upstream == ("alpha",)


def test_independent_stage_plan_assumes_ancestors() -> None:
    registry, _runners = fixture_registry()
    plan = select_plan(
        registry.dependencies(),
        profile_stages=FIXTURE_PROFILE_STAGES,
        optional_stages=FIXTURE_OPTIONAL,
        from_stage="gamma",
        to_stage="gamma",
    )
    assert plan.execute == ("gamma",)
    assert plan.assumed_upstream == ("alpha", "beta")


def test_invalid_range_and_unknown_stage_fail() -> None:
    registry, _runners = fixture_registry()
    deps = registry.dependencies()
    with pytest.raises(InvalidRangeError):
        select_plan(
            deps,
            profile_stages=FIXTURE_PROFILE_STAGES,
            optional_stages=FIXTURE_OPTIONAL,
            from_stage="omega",
            to_stage="gamma",
        )
    with pytest.raises(UnknownStageError):
        select_plan(
            deps,
            profile_stages=FIXTURE_PROFILE_STAGES,
            optional_stages=FIXTURE_OPTIONAL,
            from_stage="missing",
        )


def test_registry_rejects_cycles_and_unknown_dependencies() -> None:
    estimate = ResourceEstimate()
    with pytest.raises(CyclicDependencyError):
        StageRegistry(
            (
                StageSpec("a", "1", ("b",), (), (), estimate, (), (), None),
                StageSpec("b", "1", ("a",), (), (), estimate, (), (), None),
            )
        )
    with pytest.raises(UnknownStageError):
        StageRegistry((StageSpec("a", "1", ("missing",), (), (), estimate, (), (), None),))

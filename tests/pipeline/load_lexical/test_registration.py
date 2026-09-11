"""The lexical load stage is registered, planned, and quality-bound."""

from pathlib import Path

from arxiv_int.features.stages import STAGE_FEATURES
from arxiv_int.pipeline.control.asset_hashes import PACKAGE_ROOT
from arxiv_int.pipeline.dag.execute import UPSTREAM_POINTERS, _output_validators
from arxiv_int.pipeline.dag.graph import ancestors, select_plan
from arxiv_int.pipeline.dag.stages import (
    OPTIONAL_STAGES,
    PRODUCTION_DEPENDENCIES,
    STAGE_OVERRIDES,
    production_registry,
)
from arxiv_int.pipeline.load_lexical.artifacts import DATASET
from arxiv_int.pipeline.load_lexical.reuse import validate_load_lexical_output
from arxiv_int.pipeline.load_lexical.stage import LoadLexicalStage
from arxiv_int.runtime.setup.requirements import IMPLEMENTED_STAGES, PROFILE_STAGES

STAGE = "load-lexical"


def test_stage_runner_is_bound_and_declared_implemented() -> None:
    spec = production_registry().get(STAGE)
    assert isinstance(spec.runner, LoadLexicalStage)
    assert spec.depends_on == ("chunk",)
    assert STAGE in IMPLEMENTED_STAGES
    assert set(STAGE_FEATURES[STAGE].required) >= {"store", "transform"}


def test_owned_declarations_name_existing_assets() -> None:
    override = STAGE_OVERRIDES[STAGE]
    assert override.contracts == ("documents", "chunks")
    assert override.validators == ("documents", "chunks")
    missing = [path for path in override.code_paths if not (Path(PACKAGE_ROOT) / path).exists()]
    assert missing == []
    assert "psycopg" in override.dependency_packages


def test_plan_reaches_the_stage_without_unimplemented_siblings() -> None:
    dependencies = PRODUCTION_DEPENDENCIES
    assert "classify" not in ancestors(STAGE, dependencies)
    plan = select_plan(
        dependencies,
        profile_stages=PROFILE_STAGES["lexical"],
        optional_stages=OPTIONAL_STAGES,
        to_stage=STAGE,
    )
    assert plan.execute[-1] == STAGE
    assert "classify" not in plan.execute
    assert set(plan.execute) <= IMPLEMENTED_STAGES


def test_output_pointer_and_validator_are_registered() -> None:
    assert UPSTREAM_POINTERS[DATASET] == "lexical"
    assert validate_load_lexical_output in _output_validators()

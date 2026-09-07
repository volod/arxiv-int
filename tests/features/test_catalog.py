import pytest

from arxiv_int.features import (
    FEATURE_GROUPS,
    STAGE_FEATURES,
    conditional_groups_for_stage,
    feature_group,
    groups_for_stage,
    optional_modules,
    providing_group,
    required_groups_for_stage,
    stages_for_group,
)


def test_every_group_name_is_unique_and_resolvable() -> None:
    names = [group.name for group in FEATURE_GROUPS]

    assert len(names) == len(set(names))
    assert [feature_group(name).name for name in names] == names


def test_unknown_group_names_the_declared_groups() -> None:
    with pytest.raises(LookupError) as error:
        feature_group("no-such-group")

    assert "lake" in str(error.value)


def test_every_declared_module_maps_back_to_its_group() -> None:
    for group in FEATURE_GROUPS:
        for module in group.modules:
            assert providing_group(module) is group


def test_an_undeclared_module_belongs_to_no_group() -> None:
    with pytest.raises(LookupError):
        providing_group("pandas")


def test_reserved_groups_declare_the_capability_that_populates_them() -> None:
    reserved = [group for group in FEATURE_GROUPS if group.reserved]

    assert reserved
    assert all(group.owner for group in reserved)
    assert all(not group.modules for group in reserved)


def test_every_stage_activates_declared_groups_only() -> None:
    for stage, spec in STAGE_FEATURES.items():
        assert spec.required == tuple(sorted(spec.required)), stage
        assert spec.conditional == tuple(sorted(spec.conditional)), stage
        assert not set(spec.required) & set(spec.conditional), stage
        assert [group.name for group in groups_for_stage(stage)] == list(spec.all_names())
        assert [group.name for group in required_groups_for_stage(stage)] == list(spec.required)
        assert [group.name for group in conditional_groups_for_stage(stage)] == list(
            spec.conditional
        )


def test_gpu_and_ui_are_conditional_on_the_stages_that_can_skip_them() -> None:
    assert "gpu" in STAGE_FEATURES["embed"].conditional
    assert "gpu" not in STAGE_FEATURES["embed"].required
    assert "gpu" in STAGE_FEATURES["facts"].conditional
    assert "gpu" not in STAGE_FEATURES["facts"].required
    assert "ui" in STAGE_FEATURES["report"].conditional
    assert "ui" not in STAGE_FEATURES["report"].required
    required = {name for spec in STAGE_FEATURES.values() for name in spec.required}
    assert "gpu" not in required
    assert "ui" not in required
    assert "embed" in stages_for_group("gpu")
    assert "report" in stages_for_group("ui")


def test_every_group_serves_at_least_one_stage() -> None:
    for group in FEATURE_GROUPS:
        assert stages_for_group(group.name), group.name


def test_unknown_stage_names_the_declared_stages() -> None:
    with pytest.raises(LookupError) as error:
        groups_for_stage("no-such-stage")

    assert "inventory" in str(error.value)


def test_optional_modules_covers_every_populated_group() -> None:
    modules = optional_modules()

    assert "pyarrow" in modules
    assert "yaml" in modules
    assert all(module in modules for group in FEATURE_GROUPS for module in group.modules)

import pytest

from arxiv_int.features import (
    FEATURE_GROUPS,
    STAGE_FEATURES,
    feature_group,
    groups_for_stage,
    optional_modules,
    providing_group,
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
    for stage, names in STAGE_FEATURES.items():
        assert names == tuple(sorted(names)), stage
        assert [group.name for group in groups_for_stage(stage)] == list(names)


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

"""Keep pyproject extras, the feature catalog, and the pinned toolchain in agreement."""

import re
import tomllib
from pathlib import Path

from arxiv_int.features import FEATURE_GROUPS
from arxiv_int.quality.project_root import discover_project_root

DEV_EXTRA = "dev"
OUTPUT_SENSITIVE_TOOLS = (
    "complexipy",
    "mypy",
    "pymarkdownlnt",
    "radon",
    "ruff",
    "shellcheck-py",
)
_DISTRIBUTION = re.compile(r"^[A-Za-z0-9._-]+")


def _pyproject() -> dict[str, object]:
    root = discover_project_root(Path(__file__).resolve().parent)
    return tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))


def _project() -> dict[str, object]:
    project = _pyproject()["project"]
    assert isinstance(project, dict)
    return project


def _extras() -> dict[str, list[str]]:
    extras = _project()["optional-dependencies"]
    assert isinstance(extras, dict)
    return extras


def _distributions(requirements: list[str]) -> set[str]:
    matches = [_DISTRIBUTION.match(requirement) for requirement in requirements]
    assert all(matches)
    return {match.group(0) for match in matches if match}


def test_every_populated_group_has_a_matching_extra() -> None:
    extras = _extras()

    for group in (group for group in FEATURE_GROUPS if not group.reserved):
        assert group.name in extras, group.name
        declared = {requirement.distribution for requirement in group.requirements}
        assert _distributions(extras[group.name]) == declared, group.name


def test_reserved_groups_have_no_extra_yet() -> None:
    extras = _extras()

    for group in (group for group in FEATURE_GROUPS if group.reserved):
        assert group.name not in extras, group.name


def test_every_extra_is_a_declared_feature_group_or_the_dev_toolchain() -> None:
    names = {group.name for group in FEATURE_GROUPS} | {DEV_EXTRA}

    assert set(_extras()) <= names


def test_every_declared_requirement_records_a_licence_and_a_purpose() -> None:
    for group in FEATURE_GROUPS:
        for requirement in group.requirements:
            assert requirement.license_id.strip(), requirement.distribution
            assert requirement.purpose.strip(), requirement.distribution


def test_output_sensitive_tooling_is_pinned_exactly() -> None:
    pins = {
        _DISTRIBUTION.match(requirement).group(0): requirement  # type: ignore[union-attr]
        for requirement in _extras()[DEV_EXTRA]
    }

    for tool in OUTPUT_SENSITIVE_TOOLS:
        assert pins[tool].startswith(f"{tool}=="), tool

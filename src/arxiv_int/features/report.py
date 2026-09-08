"""Human-readable inventory of optional feature groups, licences, and install commands."""

import textwrap

from arxiv_int.features.catalog import (
    FEATURE_GROUPS,
    STAGE_FEATURES,
    groups_for_stage,
    stages_for_group,
)
from arxiv_int.features.guard import group_status, install_command
from arxiv_int.features.model import FeatureGroup
from arxiv_int.metadata import project_info

LINE_WIDTH = 96


def _stage_phrase(stage: str, group_name: str) -> str:
    spec = STAGE_FEATURES[stage]
    if group_name in spec.conditional:
        return f"{stage} (conditional)"
    return stage


def group_lines(group: FeatureGroup, *, stage: str | None = None) -> list[str]:
    """Return the reported lines for one declared group."""
    stages = ", ".join(_stage_phrase(item, group.name) for item in stages_for_group(group.name))
    stages = stages or "none"
    lines = [f"{group.name} [{group_status(group)}] {group.summary}"]
    lines.extend(
        textwrap.wrap(
            f"stages: {stages}",
            width=LINE_WIDTH,
            initial_indent="  ",
            subsequent_indent="    ",
        )
    )
    if stage is not None and group.name in STAGE_FEATURES[stage].conditional:
        lines.append("  requirement: conditional")
    if group.reserved:
        lines.append(f"  reserved for capability: {group.owner}")
    else:
        lines.append(f"  install: {install_command(group)}")
        lines.extend(
            f"  requires: {item.distribution} ({item.license_id}) -- {item.purpose}"
            for item in group.requirements
        )
    lines.extend(f"  system: {dependency}" for dependency in group.system_dependencies)
    return lines


def inventory_lines(stage: str | None = None) -> list[str]:
    """Return the full feature inventory, or only the groups one stage activates."""
    info = project_info()
    groups = FEATURE_GROUPS if stage is None else groups_for_stage(stage)
    noun = "feature group" if len(groups) == 1 else "feature groups"
    scope = noun if stage is None else f"{noun} for stage '{stage}'"
    header = f"{info.distribution} {info.version}: {len(groups)} {scope}"
    return [header, *(line for group in groups for line in group_lines(group, stage=stage))]

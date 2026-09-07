"""Optional feature groups that keep heavy stacks out of the core install."""

from arxiv_int.features.catalog import (
    FEATURE_GROUPS,
    STAGE_FEATURES,
    conditional_groups_for_stage,
    feature_group,
    groups_for_stage,
    optional_modules,
    providing_group,
    required_groups_for_stage,
    stage_features,
    stages_for_group,
)
from arxiv_int.features.guard import (
    INSTALLED,
    MISSING,
    RESERVED,
    MissingFeatureError,
    group_status,
    install_command,
    module_available,
    require_module,
)
from arxiv_int.features.model import FeatureGroup, Requirement, StageFeatureSet
from arxiv_int.features.report import group_lines, inventory_lines

__all__ = [
    "FEATURE_GROUPS",
    "INSTALLED",
    "MISSING",
    "RESERVED",
    "STAGE_FEATURES",
    "FeatureGroup",
    "MissingFeatureError",
    "Requirement",
    "StageFeatureSet",
    "conditional_groups_for_stage",
    "feature_group",
    "group_lines",
    "group_status",
    "groups_for_stage",
    "install_command",
    "inventory_lines",
    "module_available",
    "optional_modules",
    "providing_group",
    "require_module",
    "required_groups_for_stage",
    "stage_features",
    "stages_for_group",
]

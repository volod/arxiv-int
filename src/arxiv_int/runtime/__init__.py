"""Portable runtime configuration and path safety."""

from arxiv_int.runtime.compose import (
    PROFILE_ALIASES,
    SUPPORTED_PROFILES,
    ComposeConfigurationError,
    compose_command,
    compose_environment,
    parse_profiles,
    prepare_service_layout,
    run_compose,
)
from arxiv_int.runtime.config import ConfigurationError, load_runtime_config, merge_config_layers
from arxiv_int.runtime.config_model import ArchiveSilo, RuntimeConfig
from arxiv_int.runtime.containment import (
    ProtectedRoot,
    containment_violation,
    erase_protected_roots,
    report_protected_roots,
    resolve_allowed_path,
)
from arxiv_int.runtime.dotenv import DotenvError, expand_references, read_dotenv
from arxiv_int.runtime.filesystem import FilesystemEvidence, inspect_filesystem
from arxiv_int.runtime.inference_config import inference_base_url, selected_backend
from arxiv_int.runtime.path_model import PathValidation, RootPlacement
from arxiv_int.runtime.paths import create_results_layout, validate_runtime_paths
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root
from arxiv_int.runtime.service_reset import (
    ServiceResetError,
    reset_service_data,
    service_data_targets,
    validate_service_reset,
)

__all__ = [
    "PROFILE_ALIASES",
    "SUPPORTED_PROFILES",
    "ArchiveSilo",
    "ComposeConfigurationError",
    "ConfigurationError",
    "DotenvError",
    "FilesystemEvidence",
    "PathValidation",
    "ProjectRootError",
    "ProtectedRoot",
    "RootPlacement",
    "RuntimeConfig",
    "ServiceResetError",
    "compose_command",
    "compose_environment",
    "containment_violation",
    "create_results_layout",
    "erase_protected_roots",
    "expand_references",
    "find_project_root",
    "inference_base_url",
    "inspect_filesystem",
    "load_runtime_config",
    "merge_config_layers",
    "parse_profiles",
    "prepare_service_layout",
    "read_dotenv",
    "report_protected_roots",
    "reset_service_data",
    "resolve_allowed_path",
    "run_compose",
    "selected_backend",
    "service_data_targets",
    "validate_runtime_paths",
    "validate_service_reset",
]

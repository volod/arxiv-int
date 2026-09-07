"""Setup-config: dotenv sync, host tools, required edits, and path safety."""

from collections.abc import Callable, Mapping
from pathlib import Path

from arxiv_int.runtime.config import ConfigurationError, load_runtime_config
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.paths import validate_runtime_paths
from arxiv_int.runtime.setup.env_file import missing_required_edits, sync_dotenv_file
from arxiv_int.runtime.setup.host import missing_host_tools
from arxiv_int.runtime.setup.model import RETRY_COMMAND, PhaseResult, reused_or_ready
from arxiv_int.runtime.setup.state import fingerprint_for

Which = Callable[[str], str | None]


def run_config_phase(
    project_root: Path,
    *,
    which: Which,
    environment: Mapping[str, str] | None = None,
    verified: dict[str, str] | None = None,
) -> tuple[PhaseResult, RuntimeConfig | None]:
    """Create or append `.env`, name required edits, and refuse unsafe roots."""
    try:
        sync_detail = sync_dotenv_file(project_root)
    except (OSError, ConfigurationError) as error:
        return PhaseResult("config", "blocked", str(error), action="fix .env.example"), None
    missing_tools = missing_host_tools(which)
    if missing_tools:
        name, action = missing_tools[0]
        return (
            PhaseResult("config", "blocked", f"missing host tool {name}", action=action),
            None,
        )
    edits = missing_required_edits(project_root, dict(environment) if environment else None)
    if edits:
        listed = ", ".join(edits)
        return (
            PhaseResult(
                "config",
                "blocked",
                f"edit .env and set {listed}",
                action=f"edit .env ({listed}), then {RETRY_COMMAND}",
            ),
            None,
        )
    try:
        config = load_runtime_config(project_root=project_root, environment=environment)
        validation = validate_runtime_paths(config)
    except (OSError, ConfigurationError, RuntimeError) as error:
        return PhaseResult("config", "blocked", str(error), action="edit .env"), None
    blocked = tuple(item for item in validation.report.findings if item.status == "blocked")
    if blocked:
        finding = blocked[0]
        return (
            PhaseResult(
                "config",
                "blocked",
                finding.detail,
                action=finding.action or "change unsafe roots in .env",
            ),
            None,
        )
    digest = fingerprint_for(sync_detail, str(config.project_root), str(config.results_dir))
    return PhaseResult(
        "config", reused_or_ready(verified, "config", digest), sync_detail, fingerprint=digest
    ), config

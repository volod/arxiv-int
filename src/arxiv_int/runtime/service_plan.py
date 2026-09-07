"""Pure service selection shared by Compose, readiness and CLI help."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.path_model import runtime_placements
from arxiv_int.stores.postgres_image.compatibility import load_age_compatibility

PROFILE_SERVICES = {
    "core": ("database",),
    "graph": ("database", "age-viewer"),
    "ui": ("database", "grafana"),
    "observability": ("database", "postgres-exporter", "prometheus"),
    "vllm": ("vllm",),
    "cadvisor": ("cadvisor",),
}
SUPPORTED_PROFILES = tuple(PROFILE_SERVICES)
PROFILE_ALIASES = {"pipeline": ("core", "ui", "observability")}
PROFILE_HELP = (
    "; ".join(f"{profile}: {', '.join(services)}" for profile, services in PROFILE_SERVICES.items())
    + "; pipeline: "
    + ", ".join(PROFILE_ALIASES["pipeline"])
)
STATE_SERVICES = ("age-viewer", "grafana", "prometheus")


class ComposeConfigurationError(ValueError):
    """An operator Compose request cannot be formed safely."""


def parse_profiles(value: str | Sequence[str]) -> tuple[str, ...]:
    """Normalize names, preserving the historical empty-request pipeline default."""
    raw = value.split() if isinstance(value, str) else value
    requested = {profile for item in raw for profile in item.replace(",", " ").split() if profile}
    if not requested:
        requested = {"pipeline"}
    unknown = sorted(requested.difference((*SUPPORTED_PROFILES, *PROFILE_ALIASES)))
    if unknown:
        raise ComposeConfigurationError("unknown Compose profile(s): " + ", ".join(unknown))
    for alias in requested.intersection(PROFILE_ALIASES):
        requested.update(PROFILE_ALIASES[alias])
        requested.remove(alias)
    return tuple(profile for profile in SUPPORTED_PROFILES if profile in requested)


@dataclass(frozen=True, slots=True)
class ServicePlan:
    """Normalized service identities and their applicable readiness requirements."""

    profiles: tuple[str, ...]
    services: tuple[str, ...]
    age_enabled: bool = True

    @property
    def database(self) -> bool:
        return "database" in self.services

    @property
    def pipeline(self) -> bool:
        return set(PROFILE_ALIASES["pipeline"]).issubset(self.profiles)

    @property
    def inference(self) -> bool:
        return self.pipeline or "vllm" in self.services

    @property
    def graph(self) -> bool:
        return "graph" in self.profiles

    @property
    def extensions(self) -> frozenset[str]:
        if not self.database:
            return frozenset()
        if self.graph and self.age_enabled:
            return frozenset(("pg_search", "vector", "age"))
        return frozenset(("pg_search", "vector"))

    def path_variables(self, config: RuntimeConfig, *, readiness: bool = False) -> frozenset[str]:
        """Select disk checks; all configured roots remain containment boundaries."""
        if readiness and self.pipeline:
            return frozenset(item.variable for item in runtime_placements(config))
        variables = {"RESULTS_DIR", "RUNS_DIR", "TMP_DIR"}
        if self.database:
            variables.update(
                item.variable
                for item in runtime_placements(config)
                if item.storage_class == "database"
            )
        if set(STATE_SERVICES).intersection(self.services):
            variables.add("SERVICE_STATE_DIR")
        if "vllm" in self.services:
            variables.add("MODEL_CACHE_DIR")
        return frozenset(variables)


def plan_services(
    profiles: str | Sequence[str],
    *,
    project_root: Path | None = None,
) -> ServicePlan:
    """Resolve a request without inspecting or preparing the filesystem."""
    selected = parse_profiles(profiles)
    age_enabled = True
    if project_root is not None:
        age_enabled = load_age_compatibility(project_root).age_enabled
    return ServicePlan(
        selected,
        tuple(dict.fromkeys(name for profile in selected for name in PROFILE_SERVICES[profile])),
        age_enabled=age_enabled,
    )


def require_graph_age(plan: ServicePlan) -> None:
    """Refuse graph startup when the AGE compatibility gate is closed."""
    if plan.graph and not plan.age_enabled:
        raise ComposeConfigurationError(
            "graph profile is disabled until docker/postgres AGE compatibility probes pass; "
            "run make postgres-image-probe WRITE_GATE=1"
        )

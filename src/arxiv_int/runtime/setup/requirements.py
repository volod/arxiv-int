"""Declarative setup requirements without importing pipeline workers."""

from dataclasses import dataclass

from arxiv_int.features.catalog import FEATURE_GROUPS, STAGE_FEATURES, feature_group
from arxiv_int.runtime.inference_config import selected_backend
from arxiv_int.runtime.setup.settings import SetupSettings, effective_service_profiles

INVESTIGATION_STAGES: tuple[str, ...] = (
    "preflight",
    "inventory",
    "extract",
    "normalize",
    "dedupe",
    "chunk",
    "classify",
    "load-lexical",
    "nlp",
    "topics",
    "entities",
    "ontology",
    "facts",
    "domain-artifacts",
    "evaluate",
    "report",
)
LEXICAL_STAGES: tuple[str, ...] = (
    "preflight",
    "inventory",
    "extract",
    "normalize",
    "dedupe",
    "chunk",
    "classify",
    "load-lexical",
    "evaluate",
    "report",
)
IMPLEMENTED_FEATURES = frozenset(group.name for group in FEATURE_GROUPS if not group.reserved)
IMPLEMENTED_STAGES = frozenset({"preflight", "evaluate"})
PROFILE_STAGES: dict[str, tuple[str, ...]] = {
    "investigation": INVESTIGATION_STAGES,
    "lexical": LEXICAL_STAGES,
}


@dataclass(frozen=True, slots=True)
class ProfileRequirements:
    """Fixture requirements for one pipeline profile until providers ship."""

    profile: str
    stages: tuple[str, ...]
    feature_groups: tuple[str, ...]
    service_profiles: str
    generation_required: bool
    missing_providers: tuple[str, ...]
    unimplemented_stages: tuple[str, ...]


def resolve_requirements(
    settings: SetupSettings, values: dict[str, str] | None = None
) -> ProfileRequirements:
    """Map a profile onto features, services, and named unavailable providers."""
    stages = PROFILE_STAGES.get(settings.pipeline_profile)
    if stages is None:
        known = ", ".join(sorted(PROFILE_STAGES))
        raise ValueError(
            f"unknown PIPELINE_PROFILE {settings.pipeline_profile!r}; expected {known}"
        )
    groups = tuple(
        dict.fromkeys(name for stage in stages for name in STAGE_FEATURES.get(stage, ()))
    )
    missing = tuple(
        name for name in groups if name not in IMPLEMENTED_FEATURES or feature_group(name).reserved
    )
    unimplemented = tuple(stage for stage in stages if stage not in IMPLEMENTED_STAGES)
    backend = selected_backend(values or {}) if values else settings.backend
    profiles = effective_service_profiles(settings)
    if backend == "vllm" and "vllm" not in profiles.split():
        profiles = f"{profiles} vllm"
    return ProfileRequirements(
        settings.pipeline_profile,
        stages,
        groups,
        profiles,
        generation_required=True,
        missing_providers=missing,
        unimplemented_stages=unimplemented,
    )

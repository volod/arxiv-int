"""Production stage dependency declarations reused from setup profile stages."""

from collections.abc import Mapping

from arxiv_int.features.catalog import STAGE_FEATURES
from arxiv_int.pipeline.dag.registry import ResourceEstimate, StageRegistry, StageSpec
from arxiv_int.runtime.setup.requirements import PROFILE_STAGES

PRODUCTION_DEPENDENCIES: Mapping[str, tuple[str, ...]] = {
    "preflight": (),
    "inventory": ("preflight",),
    "extract": ("inventory",),
    "normalize": ("extract",),
    "dedupe": ("inventory", "normalize"),
    "chunk": ("normalize", "dedupe"),
    "classify": ("inventory", "normalize"),
    "load-lexical": ("chunk",),
    "nlp": ("normalize", "chunk"),
    "embed": ("chunk",),
    "load-vector": ("embed",),
    "topics": ("nlp",),
    "entities": ("nlp",),
    "ontology": (),
    "facts": ("entities", "ontology"),
    "graph": ("facts",),
    "domain-artifacts": ("facts",),
    "evaluate": ("load-lexical", "topics", "facts", "domain-artifacts"),
    "report": ("evaluate",),
}

OPTIONAL_STAGES: frozenset[str] = frozenset({"embed", "load-vector", "graph"})
GPU_STAGES: frozenset[str] = frozenset({"embed", "facts"})


def profile_stage_names(profile: str) -> tuple[str, ...]:
    """Return the setup-owned required stage list for one pipeline profile."""
    try:
        return PROFILE_STAGES[profile]
    except KeyError as error:
        known = ", ".join(sorted(PROFILE_STAGES))
        raise ValueError(f"unknown PIPELINE_PROFILE {profile!r}; expected {known}") from error


def production_specs() -> tuple[StageSpec, ...]:
    """Return production specs without runners; bind runners at registry build."""
    missing = [name for name in PRODUCTION_DEPENDENCIES if name not in STAGE_FEATURES]
    if missing:
        listed = ", ".join(missing)
        raise RuntimeError(f"production stages missing STAGE_FEATURES entries: {listed}")
    specs: list[StageSpec] = []
    for name, depends_on in PRODUCTION_DEPENDENCIES.items():
        gpu = name in GPU_STAGES
        specs.append(
            StageSpec(
                name=name,
                version="1",
                depends_on=depends_on,
                required_inputs=depends_on,
                conditional_inputs=(),
                resource_estimate=ResourceEstimate(gpu_required=gpu),
                validators=(),
                dbt_select=(),
                runner=None,
                optional=name in OPTIONAL_STAGES,
            )
        )
    return tuple(specs)


def production_registry() -> StageRegistry:
    """Bind shipped runners onto production specs; others remain unregistered."""
    from arxiv_int.evaluation.evaluate.stage import EvaluateStage
    from arxiv_int.pipeline.publish.preflight import PreflightStage

    return (
        StageRegistry(production_specs())
        .with_runner("preflight", PreflightStage())
        .with_runner("evaluate", EvaluateStage())
    )

"""Production stage dependency declarations reused from setup profile stages."""

from collections.abc import Mapping
from dataclasses import dataclass, replace

from arxiv_int.features.catalog import STAGE_FEATURES
from arxiv_int.pipeline.dag.registry import ResourceEstimate, StageRegistry, StageSpec
from arxiv_int.runtime.setup.requirements import PROFILE_STAGES

PRODUCTION_DEPENDENCIES: Mapping[str, tuple[str, ...]] = {
    "preflight": (),
    "inventory": ("preflight",),
    "extract": ("inventory",),
    "normalize": ("extract",),
    "dedupe": ("normalize",),
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

_QUALITY_PATHS: tuple[str, ...] = ("data_quality/rules", "data_quality/engine")
_LAKE_PACKAGES: tuple[str, ...] = ("pyarrow", "polars", "pandera", "sqlalchemy")
# The lake publisher reuses the inventory publication, validation and probing helpers,
# so every lake stage executes them and must own their identity.
_LAKE_PUBLISH_PATHS: tuple[str, ...] = (
    "pipeline/inventory/archives.py",
    "pipeline/inventory/checkpoint.py",
    "pipeline/inventory/counts.py",
    "pipeline/inventory/detect.py",
    "pipeline/inventory/probe.py",
    "pipeline/inventory/publish.py",
    "pipeline/inventory/read.py",
    "pipeline/inventory/validate.py",
)
_LAKE_PATHS: tuple[str, ...] = ("pipeline/lake", *_LAKE_PUBLISH_PATHS, *_QUALITY_PATHS)


@dataclass(frozen=True, slots=True)
class StageOverride:
    """Producer-owned declarations layered onto one generated stage spec."""

    contracts: tuple[str, ...] = ()
    validators: tuple[str, ...] = ()
    code_paths: tuple[str, ...] = ()
    dependency_packages: tuple[str, ...] = ()


STAGE_OVERRIDES: Mapping[str, StageOverride] = {
    "inventory": StageOverride(
        contracts=("source-occurrences",),
        validators=("source-occurrences",),
        code_paths=("pipeline/inventory", *_QUALITY_PATHS),
        dependency_packages=(*_LAKE_PACKAGES, "charset-normalizer"),
    ),
    "extract": StageOverride(
        contracts=("documents", "spans"),
        validators=("documents", "spans"),
        code_paths=("extraction", "pipeline/inventory/stage.py", *_LAKE_PATHS),
        dependency_packages=("iscc-tika", *_LAKE_PACKAGES),
    ),
    "normalize": StageOverride(
        contracts=("normalized-documents",),
        validators=("normalized-documents",),
        code_paths=(
            "pipeline/normalize",
            "extraction/artifacts.py",
            "extraction/model.py",
            "resources/language",
            *_LAKE_PATHS,
        ),
        dependency_packages=_LAKE_PACKAGES,
    ),
    "dedupe": StageOverride(
        contracts=("duplicate-groups",),
        validators=("duplicate-groups",),
        code_paths=("pipeline/dedupe", "pipeline/normalize/artifacts.py", *_LAKE_PATHS),
        dependency_packages=_LAKE_PACKAGES,
    ),
    "chunk": StageOverride(
        contracts=("chunks",),
        validators=("chunks",),
        code_paths=(
            "pipeline/chunk",
            "pipeline/dedupe/artifacts.py",
            "pipeline/normalize/artifacts.py",
            "pipeline/normalize/text.py",
            *_LAKE_PATHS,
        ),
        dependency_packages=_LAKE_PACKAGES,
    ),
    "classify": StageOverride(
        contracts=("file-classifications", "classification-classes"),
        validators=("file-classifications", "classification-classes"),
        code_paths=(
            "classification",
            "extraction/artifacts.py",
            "extraction/model.py",
            "pipeline/normalize/artifacts.py",
            "runtime/config.py",
            "runtime/config_schema.py",
            "runtime/dotenv.py",
            "runtime/inference_config.py",
            "runtime/project_root.py",
            "resources/configs/classification",
            *_LAKE_PATHS,
        ),
        dependency_packages=_LAKE_PACKAGES,
    ),
    "load-lexical": StageOverride(
        contracts=("documents", "chunks"),
        validators=("documents", "chunks"),
        code_paths=(
            "pipeline/load_lexical",
            "pipeline/chunk/artifacts.py",
            "pipeline/normalize/artifacts.py",
            # The load projects extracted rows, then builds the projection through dbt
            # against the configured store, so it owns those adapters as well.
            "contracts/lint",
            "contracts/migrations",
            "data_quality/generate",
            "extraction",
            "readiness/report.py",
            "retrieval/projection.py",
            "runtime",
            "stores/postgres",
            "stores/postgres_image",
            "stores/projections",
            "transformations",
            *_LAKE_PATHS,
        ),
        dependency_packages=(*_LAKE_PACKAGES, "psycopg", "dbt-postgres"),
    ),
    "evaluate": StageOverride(
        code_paths=(
            "evaluation",
            "retrieval",
            "runtime/config_schema.py",
            "runtime/inference_config.py",
            "runtime/project_root.py",
        )
    ),
}


def profile_stage_names(profile: str) -> tuple[str, ...]:
    """Return the setup-owned required stage list for one pipeline profile."""
    try:
        return PROFILE_STAGES[profile]
    except KeyError as error:
        known = ", ".join(sorted(PROFILE_STAGES))
        raise ValueError(f"unknown PIPELINE_PROFILE {profile!r}; expected {known}") from error


def production_specs() -> tuple[StageSpec, ...]:
    """Return production specs without runners; bind runners at registry build."""
    from arxiv_int.extraction.tools import extraction_tool_versions

    missing = [name for name in PRODUCTION_DEPENDENCIES if name not in STAGE_FEATURES]
    if missing:
        listed = ", ".join(missing)
        raise RuntimeError(f"production stages missing STAGE_FEATURES entries: {listed}")
    specs: list[StageSpec] = []
    for name, depends_on in PRODUCTION_DEPENDENCIES.items():
        spec = StageSpec(
            name=name,
            version="1",
            depends_on=depends_on,
            required_inputs=depends_on,
            conditional_inputs=(),
            resource_estimate=ResourceEstimate(gpu_required=name in GPU_STAGES),
            validators=(),
            dbt_select=(),
            runner=None,
            optional=name in OPTIONAL_STAGES,
        )
        override = STAGE_OVERRIDES.get(name)
        if override is not None:
            spec = replace(
                spec,
                contracts=override.contracts,
                validators=override.validators,
                code_paths=override.code_paths,
                dependency_packages=override.dependency_packages,
            )
        if name == "extract":
            spec = replace(spec, tools=extraction_tool_versions())
        specs.append(spec)
    return tuple(specs)


def production_registry() -> StageRegistry:
    """Bind shipped runners onto production specs; others remain unregistered."""
    from arxiv_int.classification.stage import ClassificationStage
    from arxiv_int.extraction.stage import ExtractionStage
    from arxiv_int.pipeline.chunk.stage import ChunkStage
    from arxiv_int.pipeline.dedupe.stage import DedupeStage
    from arxiv_int.pipeline.inventory.stage import InventoryStage
    from arxiv_int.pipeline.load_lexical.stage import LoadLexicalStage
    from arxiv_int.pipeline.normalize.stage import NormalizeStage
    from arxiv_int.pipeline.publish.preflight import PreflightStage

    return (
        StageRegistry(production_specs())
        .with_runner("preflight", PreflightStage())
        .with_runner("inventory", InventoryStage())
        .with_runner("extract", ExtractionStage())
        .with_runner("normalize", NormalizeStage())
        .with_runner("dedupe", DedupeStage())
        .with_runner("chunk", ChunkStage())
        .with_runner("classify", ClassificationStage())
        .with_runner("load-lexical", LoadLexicalStage())
    )

"""Declared optional feature groups and the pipeline stages that activate them.

This catalog is the single source of truth for optional dependency identity, licence, and
purpose. `pyproject.toml` owns version pins for the groups that carry members; a group with no
members is reserved for the capability named by `owner` and has no extra yet.
"""

from collections.abc import Mapping

from arxiv_int.features.model import FeatureGroup, Requirement

FEATURE_GROUPS: tuple[FeatureGroup, ...] = (
    FeatureGroup(
        name="contracts",
        summary="ODCS contract loading and JSON Schema validation",
        owner="contract-governance",
        requirements=(
            Requirement(
                "jsonschema", "jsonschema", "MIT", "validate contracts and generated schemas"
            ),
            Requirement("pyyaml", "yaml", "MIT", "load contract, mapping, and profile documents"),
        ),
    ),
    FeatureGroup(
        name="embeddings",
        summary="multilingual embedding and reranking model runtimes",
        owner="semantic-retrieval",
    ),
    FeatureGroup(
        name="evaluation",
        summary="retrieval, extraction, and linkage metrics with paired verdicts",
        owner="evaluation-foundation",
    ),
    FeatureGroup(
        name="extraction",
        summary="Tika, layout, and OCR lanes for text and structure extraction",
        owner="corpus-foundation",
        system_dependencies=(
            "a reachable Apache Tika server for the baseline lane",
            "tesseract-ocr and ocrmypdf for the scanned-PDF lane",
        ),
    ),
    FeatureGroup(
        name="gpu",
        summary="local GPU model runtimes for embedding, reranking, and generation",
        owner="local-inference",
        system_dependencies=("an NVIDIA driver and CUDA runtime matching the pinned profile",),
    ),
    FeatureGroup(
        name="graph",
        summary="RDF and SHACL ontology assets exported beside the graph projection",
        owner="identity-ontology-graph",
        requirements=(
            Requirement(
                "pyshacl", "pyshacl", "Apache-2.0", "validate ontology assets against shapes"
            ),
            Requirement(
                "rdflib", "rdflib", "BSD-3-Clause", "read and write Turtle ontology assets"
            ),
        ),
    ),
    FeatureGroup(
        name="inference",
        summary="provider-neutral HTTP client for local Ollama and vLLM endpoints",
        owner="local-inference",
        requirements=(
            Requirement("httpx", "httpx", "BSD-3-Clause", "call local endpoints with timeouts"),
        ),
        system_dependencies=("an Ollama system service or the optional vLLM Compose profile",),
    ),
    FeatureGroup(
        name="lake",
        summary="partitioned Parquet and Avro datasets with out-of-core analysis",
        owner="corpus-foundation",
        requirements=(
            Requirement("duckdb", "duckdb", "MIT", "query normalized datasets out of core"),
            Requirement("pyarrow", "pyarrow", "Apache-2.0", "read and write partitioned artifacts"),
        ),
    ),
    FeatureGroup(
        name="nlp",
        summary="Russian morphology, terminology, and named-entity models",
        owner="russian-nlp",
    ),
    FeatureGroup(
        name="store",
        summary="canonical PostgreSQL access for bulk load, control tables, and projections",
        owner="canonical-store",
        requirements=(
            Requirement("psycopg", "psycopg", "LGPL-3.0-only", "connect and stream binary COPY"),
        ),
        system_dependencies=("a reachable PostgreSQL service with the required extensions",),
    ),
    FeatureGroup(
        name="ui",
        summary="report rendering and local dashboard assets",
        owner="discovery-visualization",
        system_dependencies=("Docker for the dashboard and graph-viewer profiles",),
    ),
)

STAGE_FEATURES: Mapping[str, tuple[str, ...]] = {
    "preflight": ("contracts", "store"),
    "inventory": ("lake",),
    "extract": ("extraction", "lake"),
    "normalize": ("lake",),
    "dedupe": ("lake",),
    "chunk": ("lake",),
    "classify": ("lake",),
    "load-lexical": ("store",),
    "nlp": ("lake", "nlp"),
    "embed": ("embeddings", "gpu", "inference", "lake"),
    "load-vector": ("store",),
    "topics": ("lake",),
    "entities": ("lake", "store"),
    "facts": ("gpu", "inference", "lake", "store"),
    "ontology": ("graph",),
    "graph": ("graph", "store"),
    "domain-artifacts": ("lake", "store"),
    "evaluate": ("evaluation", "lake"),
    "report": ("lake", "store", "ui"),
}

_BY_NAME = {group.name: group for group in FEATURE_GROUPS}


def feature_group(name: str) -> FeatureGroup:
    """Return one declared group or name the groups that exist."""
    if name not in _BY_NAME:
        known = ", ".join(sorted(_BY_NAME))
        raise LookupError(f"unknown feature group '{name}'; declared groups are {known}")
    return _BY_NAME[name]


def providing_group(module: str) -> FeatureGroup:
    """Return the group that declares one optional import name."""
    for group in FEATURE_GROUPS:
        if module in group.modules:
            return group
    raise LookupError(f"module '{module}' is not declared by any feature group")


def groups_for_stage(stage: str) -> tuple[FeatureGroup, ...]:
    """Return the groups one pipeline stage needs before it can run."""
    if stage not in STAGE_FEATURES:
        known = ", ".join(STAGE_FEATURES)
        raise LookupError(f"unknown stage '{stage}'; declared stages are {known}")
    return tuple(feature_group(name) for name in STAGE_FEATURES[stage])


def stages_for_group(name: str) -> tuple[str, ...]:
    """Return the pipeline stages that activate one declared group."""
    feature_group(name)
    return tuple(stage for stage, groups in STAGE_FEATURES.items() if name in groups)


def optional_modules() -> frozenset[str]:
    """Return every import name that must stay outside the core import graph."""
    return frozenset(module for group in FEATURE_GROUPS for module in group.modules)

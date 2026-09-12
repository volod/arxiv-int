"""Pipeline stage to required and conditional feature-group bindings."""

from collections.abc import Mapping

from arxiv_int.features.model import StageFeatureSet


def _features(*required: str, conditional: tuple[str, ...] = ()) -> StageFeatureSet:
    return StageFeatureSet(required=tuple(sorted(required)), conditional=tuple(sorted(conditional)))


STAGE_FEATURES: Mapping[str, StageFeatureSet] = {
    "preflight": _features("contracts", "store"),
    "inventory": _features("lake"),
    "extract": _features("extraction", "lake"),
    "normalize": _features("data-quality", "lake"),
    "dedupe": _features("data-quality", "lake"),
    "chunk": _features("data-quality", "lake"),
    "classify": _features("data-quality", "lake"),
    "load-lexical": _features("data-quality", "lake", "store", "transform"),
    "nlp": _features("data-quality", "lake", "nlp"),
    "embed": _features("embeddings", "inference", "lake", conditional=("gpu",)),
    "load-vector": _features("store"),
    "topics": _features("data-quality", "lake"),
    "entities": _features("data-quality", "lake", "store"),
    "concepts": _features(
        "concepts", "data-quality", "inference", "lake", "nlp", "store", conditional=("gpu",)
    ),
    "facts": _features("data-quality", "inference", "lake", "store", conditional=("gpu",)),
    "concept-relations": _features(
        "concepts", "data-quality", "inference", "lake", "store", conditional=("gpu",)
    ),
    "ontology": _features("graph"),
    "refinder": _features(
        "concepts",
        "data-quality",
        "inference",
        "lake",
        "store",
        conditional=("embeddings", "gpu"),
    ),
    "graph-communities": _features("data-quality", "graph-analytics", "lake", "store", "transform"),
    "graph-metrics": _features("data-quality", "graph-analytics", "lake", "store", "transform"),
    "graph": _features("graph", "store", "transform"),
    "domain-artifacts": _features("data-quality", "lake", "store", "transform"),
    "agent-diagnostics": _features(
        "agents", "data-quality", "inference", "lake", "store", conditional=("gpu",)
    ),
    "evaluate": _features("data-quality", "evaluation", "lake"),
    "report": _features("data-quality", "lake", "store", "transform", conditional=("ui",)),
}

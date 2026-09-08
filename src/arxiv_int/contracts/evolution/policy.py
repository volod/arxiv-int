"""Projection and semantic consequence classification on top of field changes."""

from typing import Any

from arxiv_int.contracts.catalog.odcs_ext import project_extension
from arxiv_int.contracts.evolution.core import (
    CHANGE_ADDITIVE,
    CHANGE_BREAKING,
    CHANGE_GRAPH_PROJECTION,
    CHANGE_IDENTICAL,
    CHANGE_REINDEX,
    CHANGE_SEMANTIC_RETARGET,
    CHANGE_VECTOR_DIMENSION,
    ChangeReport,
    classify_change,
)


def projection_snapshot(odcs_document: dict[str, Any]) -> dict[str, Any]:
    """Extract search/vector/graph hints that trigger non-row-schema consequences."""
    extension = project_extension(odcs_document.get("customProperties")) or {}
    snapshot: dict[str, Any] = {}
    for key in ("search", "vector", "graph"):
        value = extension.get(key)
        if isinstance(value, dict):
            snapshot[key] = dict(sorted(value.items()))
    return snapshot


def classify_projection_change(
    baseline: dict[str, Any], current: dict[str, Any]
) -> ChangeReport | None:
    """Return the strongest projection consequence, or None when projections match."""
    details: list[str] = []
    klass: str | None = None
    base_search = baseline.get("search") or {}
    cur_search = current.get("search") or {}
    if base_search != cur_search:
        klass = CHANGE_REINDEX
        details.append("search tokenizer or textFields changed")
    base_vector = baseline.get("vector") or {}
    cur_vector = current.get("vector") or {}
    if base_vector.get("defaultDimensions") != cur_vector.get("defaultDimensions"):
        klass = CHANGE_VECTOR_DIMENSION
        details.append("vector defaultDimensions changed")
    elif base_vector != cur_vector and klass is None:
        klass = CHANGE_REINDEX
        details.append("vector index configuration changed")
    base_graph = baseline.get("graph") or {}
    cur_graph = current.get("graph") or {}
    if base_graph != cur_graph:
        if klass is None:
            klass = CHANGE_GRAPH_PROJECTION
        details.append("graph projection labels or endpoints changed")
    if klass is None:
        return None
    return ChangeReport(klass, tuple(details))


def classify_semantic_change(
    baseline_hash: str | None, current_hash: str | None
) -> ChangeReport | None:
    """Classify semantic metadata retarget when fingerprints diverge."""
    if not baseline_hash and not current_hash:
        return None
    if baseline_hash == current_hash:
        return None
    return ChangeReport(
        CHANGE_SEMANTIC_RETARGET,
        ("semanticMetadataHash changed",),
    )


def merge_change_reports(*reports: ChangeReport | None) -> ChangeReport:
    """Combine reports preferring major consequences over minor/identical."""
    priority = {
        CHANGE_BREAKING: 60,
        CHANGE_VECTOR_DIMENSION: 50,
        CHANGE_SEMANTIC_RETARGET: 40,
        CHANGE_REINDEX: 30,
        CHANGE_GRAPH_PROJECTION: 20,
        CHANGE_ADDITIVE: 10,
        CHANGE_IDENTICAL: 0,
    }
    selected = ChangeReport(CHANGE_IDENTICAL)
    details: list[str] = []
    for report in reports:
        if report is None:
            continue
        details.extend(report.details)
        if priority.get(report.change_class, 0) > priority.get(selected.change_class, 0):
            selected = report
    if selected.change_class == CHANGE_IDENTICAL and details:
        for report in reports:
            if report is not None and report.change_class == CHANGE_ADDITIVE:
                return ChangeReport(CHANGE_ADDITIVE, tuple(details))
    return ChangeReport(selected.change_class, tuple(details) if details else selected.details)


def classify_contract_evolution(
    *,
    baseline_fields: dict[str, Any],
    current_fields: dict[str, Any],
    baseline_projections: dict[str, Any],
    current_projections: dict[str, Any],
    baseline_semantic_hash: str | None,
    current_semantic_hash: str | None,
) -> ChangeReport:
    """Classify the full physical + projection + semantic consequence set."""
    return merge_change_reports(
        classify_change(baseline_fields, current_fields),
        classify_projection_change(baseline_projections, current_projections),
        classify_semantic_change(baseline_semantic_hash, current_semantic_hash),
    )

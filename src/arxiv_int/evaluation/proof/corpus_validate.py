"""Complete corpus proof validation without extracting or normalizing source content."""

from pathlib import Path
from typing import Any

from arxiv_int.evaluation.proof.corpus_accounting import (
    account_duplicates,
    account_extraction,
    account_normalization,
    check_sources,
)
from arxiv_int.evaluation.proof.corpus_artifacts import STAGES, require, validate_execution
from arxiv_int.evaluation.proof.corpus_offsets import check_chunks, check_spans, check_views
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.persist import RunStatus


def validate_corpus(
    context: RunContext, status: RunStatus
) -> tuple[dict[str, tuple[Path, dict[str, Any]]], dict[str, Any]]:
    """Refuse failed stages, missing rows, corrupt artifacts and broken source anchors."""
    require(not status.halted, "corpus run halted")
    observed = [item for item in status.executions if item.stage in STAGES]
    require(len(observed) == len(STAGES), "corpus proof requires exactly one shard per stage")
    selected = {item.stage: item for item in observed}
    require(set(selected) == set(STAGES), "corpus proof is missing a required stage")
    snapshots = {name: validate_execution(selected[name], context.project_root) for name in STAGES}
    inventory = check_sources(snapshots["inventory"][0], context)
    extraction = snapshots["extract"][1]
    normalization = snapshots["normalize"][1]
    documents, accounting = account_extraction(inventory, extraction)
    spans = check_spans(documents, extraction, inventory)
    normalized = account_normalization(documents, normalization)
    check_views(normalized, extraction, normalization)
    suppressed, duplicates = account_duplicates(normalized, snapshots["dedupe"][1])
    chunks = check_chunks(normalized, documents, suppressed, snapshots["chunk"][1], normalization)
    return snapshots, {
        "accounting": accounting,
        "extraction_coverage": extraction["coverage"],
        "formats": extraction["formats"],
        "spans": spans,
        "normalized_documents": len(normalized),
        "duplicates": duplicates,
        "chunks": chunks,
    }

"""Synthetic corpus accounting, source anchors and refusal boundaries."""

import json
from pathlib import Path

import pytest

from arxiv_int.evaluation.evaluate.errors import ProofIntegrityError
from arxiv_int.evaluation.proof.corpus_accounting import (
    account_duplicates,
    account_extraction,
    account_normalization,
)
from arxiv_int.evaluation.proof.corpus_artifacts import (
    rows,
    validate_contracts,
    validate_inventory_rows,
)
from arxiv_int.evaluation.proof.corpus_offsets import check_chunks, check_spans, check_views
from tests.pipeline.chain import ChainRun, run_chain


@pytest.fixture(scope="module")
def corpus(tmp_path_factory: pytest.TempPathFactory) -> tuple[ChainRun, dict, dict]:
    chain = run_chain(tmp_path_factory.mktemp("corpus-proof"))
    summaries = {
        stage: json.loads(chain.manifest(getattr(chain, stage)).read_text())
        for stage in ("extract", "normalize", "dedupe", "chunk")
    }
    inventory_path = next(chain.context.results_dir.rglob("inventory.json"))
    inventory_summary = json.loads(inventory_path.read_text())
    validate_inventory_rows(inventory_path, inventory_summary, Path.cwd())
    inventory = {
        row["occurrence_id"]: extra for row, extra in rows(inventory_path.parent, "occurrence_id")
    }
    return chain, summaries, inventory


def test_all_corpus_contracts_accounting_and_offsets(corpus: tuple) -> None:
    _chain, summaries, inventory = corpus
    for stage, contracts in {
        "extract": ("documents", "spans"),
        "normalize": ("normalized-documents",),
        "dedupe": ("duplicate-groups",),
        "chunk": ("chunks",),
    }.items():
        validate_contracts(summaries[stage], contracts, Path.cwd())
    documents, counts = account_extraction(inventory, summaries["extract"])
    assert counts["occurrences"] == len(inventory)
    assert check_spans(documents, summaries["extract"], inventory) > 0
    normalized = account_normalization(documents, summaries["normalize"])
    check_views(normalized, summaries["extract"], summaries["normalize"])
    suppressed, duplicates = account_duplicates(normalized, summaries["dedupe"])
    assert duplicates["largest_component"] >= 2
    assert (
        check_chunks(normalized, documents, suppressed, summaries["chunk"], summaries["normalize"])
        > 0
    )


def test_unaccounted_inventory_occurrence_refuses(corpus: tuple) -> None:
    _chain, summaries, inventory = corpus
    with pytest.raises(ProofIntegrityError, match="unaccounted"):
        account_extraction({**inventory, "unaccounted": {}}, summaries["extract"])


def test_quarantine_counts_cannot_be_claimed_without_rows(corpus: tuple) -> None:
    _chain, summaries, inventory = corpus
    with pytest.raises(ProofIntegrityError, match="quarantine count"):
        account_extraction(inventory, {**summaries["extract"], "quarantined": 999})


def test_suppressed_document_cannot_publish_chunks(corpus: tuple) -> None:
    _chain, summaries, inventory = corpus
    documents, _ = account_extraction(inventory, summaries["extract"])
    normalized = account_normalization(documents, summaries["normalize"])
    first = next(rows(Path(summaries["chunk"]["roots"]["chunks"]), "chunk_id"))[0]
    with pytest.raises(ProofIntegrityError, match="suppressed"):
        check_chunks(
            normalized,
            documents,
            {first["document_id"]},
            summaries["chunk"],
            summaries["normalize"],
        )


def test_component_histogram_reproduces_after_json_roundtrip(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from arxiv_int.evaluation.bundles.manifest import canonical_json

    memberships = []
    for size in (2, 10):
        for index in range(size):
            memberships.append(
                (
                    {
                        "group_id": str(size),
                        "document_id": f"doc-{size}-{index}",
                        "role": "representative" if index == 0 else "member",
                        "suppressed": index != 0,
                    },
                    {},
                )
            )
    monkeypatch.setattr(
        "arxiv_int.evaluation.proof.corpus_accounting.rows", lambda *_args: iter(memberships)
    )
    normalized = {row["document_id"]: {} for row, _ in memberships}
    summary = {
        "roots": {"duplicate-groups": "synthetic"},
        "duplicate_groups": 2,
        "duplicate_memberships": 12,
        "suppressed_documents": 10,
    }
    _suppressed, metrics = account_duplicates(normalized, summary)
    encoded = canonical_json(metrics)
    assert canonical_json(json.loads(encoded)) == encoded

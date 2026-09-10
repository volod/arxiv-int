"""Cross-stage occurrence, document, quarantine and duplicate accounting."""

from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from arxiv_int.evaluation.proof.corpus_artifacts import require, rows
from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.inventory.walk import open_source
from arxiv_int.pipeline.lake.artifacts import read_jsonl
from arxiv_int.pipeline.run.context import RunContext


def check_sources(path: Path, context: RunContext) -> dict[str, dict[str, Any]]:
    """Verify every hashed physical occurrence still matches the read-only source bytes."""
    import hashlib
    import os

    sources = {s.silo_id: s.root for s in context.silos}
    inventory: dict[str, dict[str, Any]] = {}
    for row, extra in rows(path.parent, "occurrence_id"):
        inventory[row["occurrence_id"]] = extra
        if extra["members"] or not extra["content_hash"]:
            continue
        digest = hashlib.sha256()
        with os.fdopen(
            open_source(sources[extra["silo_id"]], extra["relative_path"]), "rb"
        ) as handle:
            while block := handle.read(1048576):
                digest.update(block)
        require(
            digest.hexdigest() == extra["content_hash"], "source content changed since inventory"
        )
    return inventory


def quarantine(root: Path, key: str) -> dict[str, str]:
    """Require a unique identity and actionable reason for each refused item."""
    result: dict[str, str] = {}
    for row in read_jsonl(root / "quarantine.jsonl"):
        identity = row[key]
        require(identity not in result and bool(row["reason"]), "invalid quarantine accounting")
        result[identity] = row["reason"]
    return result


def account_extraction(
    inventory: dict[str, dict[str, Any]], summary: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Every inventory item becomes exactly one document occurrence or quarantine."""
    roots = {key: Path(value) for key, value in summary["roots"].items()}
    documents: dict[str, dict[str, Any]] = {}
    for row, extra in rows(roots["documents"], "document_id"):
        identity = row["document_id"]
        require(identity not in documents, "duplicate extracted document")
        text_path = roots["documents"] / "text" / f"{identity}.txt"
        require(hash_file(text_path)[0] == extra["text_sha256"], "document text hash mismatch")
        require(
            len(text_path.read_bytes().decode("utf-8")) == row["text_chars"],
            "document length mismatch",
        )
        documents[identity] = row
    mapped: set[str] = set()
    represented: set[str] = set()
    for item in read_jsonl(roots["documents"] / "occurrences.jsonl"):
        occurrence, document = item["occurrence_id"], item["document_id"]
        require(occurrence in inventory and occurrence not in mapped, "invalid occurrence mapping")
        require(document in documents, "occurrence refers to missing document")
        require(
            inventory[occurrence]["content_hash"] == documents[document]["content_hash"],
            "content mapping mismatch",
        )
        mapped.add(occurrence)
        represented.add(document)
    refused = quarantine(roots["quarantine"], "occurrence_id")
    require(not (mapped & refused.keys()), "occurrence both extracted and quarantined")
    require(mapped | refused.keys() == inventory.keys(), "unaccounted inventory occurrence")
    require(represented == documents.keys(), "document has no source occurrence")
    require(len(documents) == summary["documents"], "document count mismatch")
    require(len(refused) == summary["quarantined"], "extraction quarantine count mismatch")
    require(len(mapped) - len(documents) == summary["reused_content"], "reuse count mismatch")
    return documents, {
        "occurrences": len(inventory),
        "documents": len(documents),
        "quarantine": dict(Counter(refused.values())),
    }


def account_normalization(
    documents: dict[str, Any], summary: dict[str, Any]
) -> dict[str, dict[str, Any]]:
    """Every extracted document is normalized or explicitly quarantined."""
    normalized: dict[str, dict[str, Any]] = {}
    for row, extra in rows(
        Path(summary["roots"]["normalized-documents"]), "normalized_document_id"
    ):
        identity = row["document_id"]
        require(identity in documents and identity not in normalized, "invalid normalized identity")
        normalized[identity] = {**row, "metadata": extra}
    refused = quarantine(Path(summary["roots"]["quarantine"]), "document_id")
    require(not normalized.keys() & refused.keys(), "normalized document also quarantined")
    require(
        normalized.keys() | refused.keys() == documents.keys(), "unaccounted extracted document"
    )
    require(len(normalized) == summary["normalized_documents"], "normalization count mismatch")
    require(len(refused) == summary["quarantined"], "normalization quarantine count mismatch")
    return normalized


def account_duplicates(
    normalized: dict[str, Any], summary: dict[str, Any]
) -> tuple[set[str], dict[str, Any]]:
    """Check representatives and report component sizes without approving semantic equivalence."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    suppressed: set[str] = set()
    memberships = 0
    for row, _extra in rows(Path(summary["roots"]["duplicate-groups"]), "duplicate_membership_id"):
        require(row["document_id"] in normalized, "duplicate group references missing document")
        groups[row["group_id"]].append(row)
        memberships += 1
        if row["suppressed"]:
            suppressed.add(row["document_id"])
    suppressing_sizes: list[int] = []
    for group in groups.values():
        representatives = [row for row in group if row["role"] == "representative"]
        require(len(representatives) == 1, "duplicate group needs exactly one representative")
        require(not representatives[0]["suppressed"], "duplicate representative is suppressed")
        if any(row["suppressed"] for row in group):
            require(
                representatives[0]["document_id"] not in suppressed,
                "suppressed group has no retained representative",
            )
            suppressing_sizes.append(len(group))
    require(len(groups) == summary["duplicate_groups"], "duplicate group count mismatch")
    require(memberships == summary["duplicate_memberships"], "duplicate membership count mismatch")
    require(len(suppressed) == summary["suppressed_documents"], "suppression count mismatch")
    return suppressed, {
        "largest_suppressing_component": max(suppressing_sizes, default=0),
        "groups": len(groups),
        "memberships": memberships,
        "largest_component": max((len(group) for group in groups.values()), default=0),
        "component_sizes": {
            str(size): count
            for size, count in Counter(len(group) for group in groups.values()).items()
        },
        "suppressed": len(suppressed),
        "suppressed_share": len(suppressed) / max(1, len(normalized)),
    }

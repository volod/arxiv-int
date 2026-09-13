"""Independent physical/member accounting and hierarchical mapping invariants."""

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from arxiv_int.classification.model import classification_id
from arxiv_int.classification.vocabulary.outcomes import EXCEPTIONAL_OUTCOMES
from arxiv_int.pipeline.lake.artifacts import read_jsonl
from tests.integration.corpus.artifacts import require, rows


def check_mapping(
    summary: dict[str, Any],
    inventory: dict[str, dict[str, Any]],
    extraction: dict[str, Any],
    normalized: dict[str, dict[str, Any]],
) -> tuple[list[tuple[dict[str, Any], dict[str, Any]]], dict[str, Any]]:
    """Reconcile every physical file and retain virtual-to-physical source identities."""
    physical = {key: row for key, row in inventory.items() if not row["members"]}
    by_location = {(row["silo_id"], row["relative_path"]): key for key, row in physical.items()}
    members = {key: row for key, row in inventory.items() if row["members"]}
    _check_members(inventory, members, by_location)
    source_documents: dict[str, set[str]] = defaultdict(set)
    for occurrence in read_jsonl(Path(extraction["roots"]["documents"]) / "occurrences.jsonl"):
        source = inventory[occurrence["occurrence_id"]]
        physical_id = by_location[(source["silo_id"], source["relative_path"])]
        if occurrence["document_id"] in normalized:
            source_documents[physical_id].add(occurrence["document_id"])
    extraction_failures = {
        item["occurrence_id"]: item["reason"]
        for item in read_jsonl(Path(extraction["roots"]["quarantine"]) / "quarantine.jsonl")
    }
    classes = {
        row["class_id"]: row
        for row, _ in rows(Path(summary["roots"]["classification-classes"]), "scheme_class_id")
    }
    found = list(rows(Path(summary["roots"]["file-classifications"]), "classification_id"))
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    truncated = 0
    for row, extra in found:
        identity = row["occurrence_id"]
        require(identity in physical and identity not in seen, "missing/duplicate physical mapping")
        seen.add(identity)
        source = physical[identity]
        require(
            (row["silo_id"], row["relative_path"]) == (source["silo_id"], source["relative_path"]),
            "mapping source location drift",
        )
        require(extra["content_hash"] == source["content_hash"], "mapping source checksum drift")
        require(
            row["classification_id"]
            == classification_id(
                identity, summary["scheme"]["scheme_id"], summary["classifier"]["classifier_id"]
            ),
            "classification identity mismatch",
        )
        _check_hierarchy(row, classes)
        _check_document_accounting(row, extra, source_documents[identity])
        primary = row["primary_class_id"]
        _check_readability(row, source, source_documents[identity], extraction_failures)
        require(row["scheme_id"] == summary["scheme"]["scheme_id"], "row scheme drift")
        require(
            row["configuration_sha256"] == summary["classifier"]["configuration_sha256"],
            "row classifier configuration drift",
        )
        require(
            row["extraction_fingerprint"] == summary["upstream"]["extraction"]["sha256"],
            "row extraction identity drift",
        )
        require(row["review_state"] == "proposed", "unreviewed mapping was promoted")
        truncated += bool(extra["truncated_document_ids"])
        counts[primary] += 1
    require(seen == physical.keys(), "unaccounted physical files")
    require(dict(counts) == summary["counts_by_primary"], "outcome count mismatch")
    require(
        summary["accounting"]
        == {
            "classified_rows": len(found),
            "physical_inventory_rows": len(physical),
            "virtual_member_rows": len(members),
            "text_budget_truncated_rows": truncated,
        },
        "classification denominator mismatch",
    )
    return found, {
        "physicalFiles": len(physical),
        "virtualMembers": len(members),
        "countsByPrimary": dict(sorted(counts.items())),
        "truncatedFiles": truncated,
    }


def _check_members(
    inventory: dict[str, dict[str, Any]],
    members: dict[str, dict[str, Any]],
    by_location: dict[tuple[str, str], str],
) -> None:
    parents = {
        (item["silo_id"], item["relative_path"], tuple(item["members"])): item
        for item in inventory.values()
    }
    for row in members.values():
        require(
            (row["silo_id"], row["relative_path"]) in by_location,
            "virtual member has no physical container",
        )
        parent = parents.get((row["silo_id"], row["relative_path"], tuple(row["members"][:-1])))
        if row["members"][-1] == "!policy":
            require(
                parent is not None
                and row["content_hash"] is None
                and row["status"] == "quarantined"
                and row["reason"] in {"archive-depth-limit", "archive-invalid-or-limit"},
                "invalid archive policy refusal marker",
            )
            continue
        require(
            parent is not None and parent["content_hash"] == row["parent_hash"],
            "virtual member parent checksum is inconsistent",
        )


def _check_readability(
    row: dict[str, Any], source: dict[str, Any], documents: set[str], failures: dict[str, str]
) -> None:
    if row["primary_class_id"] == "unreadable":
        require(not documents, "readable file was declared unreadable")
        require(
            source["status"] != "ready"
            or row["occurrence_id"] in failures
            or row["failure_reason"].startswith("normalization-"),
            "unreadable outcome has no upstream failure",
        )
    else:
        require(bool(documents), "usable result has no normalized source")


def _check_hierarchy(row: dict[str, Any], classes: dict[str, dict[str, Any]]) -> None:
    primary = row["primary_class_id"]
    require(primary in classes, "primary class is unknown")
    path: list[str] = []
    current = primary
    while current:
        require(current in classes and current not in path, "broken/cyclic class hierarchy")
        path.insert(0, current)
        current = classes[current]["parent_class_id"]
    require(row["ancestor_path"].split(">") == path, "primary ancestor path is inconsistent")
    alternates = json.loads(row["alternate_class_ids_json"])
    require(len(alternates) == len(set(alternates)), "duplicate alternate classes")
    require(
        set(alternates) <= classes.keys() - EXCEPTIONAL_OUTCOMES - {primary},
        "invalid alternate class",
    )
    if primary in EXCEPTIONAL_OUTCOMES:
        require(bool(row["failure_reason"]) and not alternates, "exception lacks failure reason")
    else:
        require(
            row["failure_reason"] is None and bool(json.loads(row["evidence_json"])),
            "ordinary assignment lacks decisive evidence",
        )
    require(0.0 <= row["confidence"] <= 1.0, "confidence is out of bounds")
    candidates = json.loads(row["scores_json"])
    require(
        all(item["class_id"] in classes and 0.0 <= item["score"] <= 1.0 for item in candidates),
        "candidate scores are invalid",
    )


def _check_document_accounting(
    row: dict[str, Any], extra: dict[str, Any], available: set[str]
) -> None:
    read = set(extra["document_ids"])
    truncated = set(extra["truncated_document_ids"])
    require(read <= available and truncated <= available, "mapping references foreign documents")
    require(read | truncated == available, "usable container/member documents were dropped")
    require(
        row["document_id"] == (sorted(read)[0] if read else None),
        "primary document pointer is inconsistent",
    )

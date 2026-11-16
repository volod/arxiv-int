"""Synthetic integrity regressions for the in-place archive cross-checks."""

import io
import json
import zipfile
from pathlib import Path
from typing import Any

import pytest

from arxiv_int.pipeline.run.persist import load_json
from tests.classification.stage_helpers import classify
from tests.classification.test_stage import _ArchiveRouter
from tests.integration.classification.evidence import check_evidence
from tests.integration.classification.mapping import _check_hierarchy, _check_members, check_mapping
from tests.integration.corpus.accounting import account_extraction, account_normalization
from tests.integration.corpus.artifacts import rows
from tests.pipeline.chain import run_chain


def test_archive_checks_resolve_normalized_spans_and_virtual_container(tmp_path: Path) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("member.txt", "Machine learning artificial intelligence data science")
    chain = run_chain(
        tmp_path,
        fixtures={
            "opaque.txt": "Structural engineering structural analysis and design",
            "random.txt": "qqqq zzzz unrelated",
            "empty.txt": "\u200b\n",
        },
        raw_fixtures={"container.zip": buffer.getvalue()},
        router=_ArchiveRouter(),
    )
    summary = load_json(chain.manifest(classify(chain)))
    inventory_path = chain.manifest(chain.inventory)
    inventory = {
        row["occurrence_id"]: extra for row, extra in rows(inventory_path.parent, "occurrence_id")
    }
    extraction = load_json(chain.manifest(chain.extract))
    normalization = load_json(chain.manifest(chain.normalize))
    documents, _ = account_extraction(inventory, extraction)
    normalized = account_normalization(documents, normalization)
    mappings, accounting = check_mapping(summary, inventory, extraction, normalized)
    evidence = check_evidence(
        mappings, normalized, documents, normalization, inventory_path, chain.context.silos
    )
    assert accounting["physicalFiles"] == 4
    assert accounting["virtualMembers"] == 1
    assert evidence["spansBySpace"]["normalized-search"] > 0
    assert evidence["resolvedMemberLocations"] == 1
    assert evidence["resolvedDocuments"] == 3

    assigned = next(row for row, _ in mappings if row["primary_class_id"].startswith("tax:"))
    spans = json.loads(assigned["evidence_json"])
    spans[0]["end"] += 1
    assigned["evidence_json"] = json.dumps(spans)
    with pytest.raises(AssertionError, match="exact token"):
        check_evidence(
            mappings, normalized, documents, normalization, inventory_path, chain.context.silos
        )


def test_member_without_physical_container_is_refused() -> None:
    member = {
        "silo_id": "one",
        "relative_path": "bundle.zip",
        "members": ["item.txt"],
        "content_hash": "member",
        "parent_hash": "container",
    }
    with pytest.raises(AssertionError, match="no physical container"):
        _check_members({"member": member}, {"member": member}, {})


@pytest.mark.parametrize("path", ["tax:leaf", "tax:other>tax:leaf"])
def test_wrong_ancestor_chain_is_refused(path: str) -> None:
    classes = {"tax:root": {"parent_class_id": None}, "tax:leaf": {"parent_class_id": "tax:root"}}
    row: dict[str, Any] = {"primary_class_id": "tax:leaf", "ancestor_path": path}
    with pytest.raises(AssertionError, match="ancestor path"):
        _check_hierarchy(row, classes)

"""Resolve actual inventory member addresses without conflating member/container hashes."""

import json
from pathlib import Path

import pytest

from arxiv_int.pipeline.inventory.model import Observation
from arxiv_int.query.evidence.model import EvidenceCatalog
from arxiv_int.query.evidence.resolve import resolve_citation
from arxiv_int.query.evidence.schema import parse_row
from tests.query.evidence._builders import document, sha256_bytes


def _catalog(*, include_container: bool = True) -> EvidenceCatalog:
    container = Observation("one", "bundle.zip", content_hash=sha256_bytes(b"container"))
    addresses = tuple(
        json.dumps([index, name], ensure_ascii=True)
        for index, name in ((0, "nested.zip"), (2, "folder/\u043e\u0442\u0447\u0435\u0442.txt"))
    )
    member = Observation(
        "one",
        "bundle.zip",
        members=addresses,
        content_hash=sha256_bytes(b"member"),
        parent_hash="nested-hash",
    )
    observations = (container, member) if include_container else (member,)
    return EvidenceCatalog(
        documents=(document("doc-member", sha256_bytes(b"member")),),
        occurrences=tuple(
            parse_row("source-occurrences", item.contract_row("scan", "run"))
            for item in observations
        ),
    )


def test_inventory_member_lookup_checks_container_and_keeps_member_identity(tmp_path: Path) -> None:
    catalog = _catalog()
    source = tmp_path / "bundle.zip"
    source.write_bytes(b"container")
    resolution = resolve_citation(catalog, "doc-member", silo_roots={"one": tmp_path})
    assert len(resolution.locations) == 1
    location = resolution.locations[0]
    assert location.status == "matching"
    assert location.content_hash == resolution.content_hash == sha256_bytes(b"member")
    assert location.container_path == "bundle.zip"
    assert len(json.loads(location.member_path)) == 2
    source.write_bytes(b"changed container")
    assert (
        resolve_citation(catalog, "doc-member", silo_roots={"one": tmp_path}).locations[0].status
        == "changed"
    )


def test_inventory_member_without_container_digest_is_not_reported_matching(tmp_path: Path) -> None:
    catalog = _catalog(include_container=False)
    (tmp_path / "bundle.zip").write_bytes(b"container")
    result = resolve_citation(catalog, "doc-member", silo_roots={"one": tmp_path})
    assert result.locations[0].status == "unchecked"


@pytest.mark.parametrize("address", ["[123]", '["not-json"]', "[]", '["[-1, \\"file.txt\\"]"]'])
def test_malformed_inventory_member_address_is_refused(address: str) -> None:
    row = Observation("one", "bundle.zip", content_hash="digest").contract_row("scan", "run")
    row["container_path"], row["member_path"] = "bundle.zip", address
    with pytest.raises(ValueError, match="member"):
        parse_row("source-occurrences", row)

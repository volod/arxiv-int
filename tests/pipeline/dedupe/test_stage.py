"""Duplicate overlays, labeled precision, and reversible grouping."""

import json
from pathlib import Path

import pytest

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dedupe.artifacts import validate_manifest
from arxiv_int.pipeline.dedupe.model import EDITION, EXACT, LEXICAL, MEMBER, NORMALIZED
from tests.pipeline.chain import ChainRun, run_chain


@pytest.fixture(scope="module")
def chain(tmp_path_factory: pytest.TempPathFactory) -> ChainRun:
    return run_chain(tmp_path_factory.mktemp("dedupe"))


def _summary(run: ChainRun) -> dict[str, object]:
    return json.loads(run.manifest(run.dedupe).read_text(encoding="ascii"))


def _rows(run: ChainRun) -> list[dict[str, object]]:
    polars = pytest.importorskip("polars")
    files = sorted(Path(str(_summary(run)["roots"]["duplicate-groups"])).glob("part-*.parquet"))
    if not files:
        return []
    return polars.read_parquet(files).to_dicts()


def _titles(run: ChainRun) -> dict[str, str]:
    extraction = json.loads(run.manifest(run.extract).read_text(encoding="ascii"))
    polars = pytest.importorskip("polars")
    files = sorted(Path(str(extraction["roots"]["documents"])).glob("part-*.parquet"))
    return {
        str(row["title"]): str(row["document_id"])
        for row in polars.read_parquet(files).to_dicts()
        if row["title"]
    }


def test_stage_proposes_duplicate_and_edition_overlays(chain: ChainRun) -> None:
    summary = _summary(chain)
    rows = _rows(chain)
    methods = {str(row["method"]) for row in rows}
    suppressed = [row for row in rows if row["suppressed"]]

    assert chain.dedupe.outcome == "produced"
    assert int(summary["duplicate_groups"]) >= 2
    assert int(summary["suppressed_documents"]) == len(suppressed)
    assert {EXACT, NORMALIZED, LEXICAL} & methods
    assert EDITION in methods
    assert all(row["role"] == MEMBER for row in suppressed)
    assert all(not row["suppressed"] for row in rows if row["method"] == EDITION)


def test_no_suppression_occurs_without_an_overlay(chain: ChainRun) -> None:
    rows = _rows(chain)
    suppressed = [row for row in rows if row["suppressed"]]
    grouped = {str(row["document_id"]) for row in rows}
    assert {str(row["document_id"]) for row in suppressed} <= grouped
    for row in suppressed:
        assert any(
            other["group_id"] == row["group_id"] and not other["suppressed"] for other in rows
        )


def test_labeled_duplicate_precision_on_the_fixture_corpus(chain: ChainRun) -> None:
    titles = _titles(chain)
    rows = [row for row in _rows(chain) if row["method"] != EDITION]
    pairs = {
        frozenset((str(row["document_id"]), str(other["document_id"])))
        for row in rows
        for other in rows
        if row["group_id"] == other["group_id"] and row["document_id"] < other["document_id"]
    }
    expected = {
        frozenset((titles[left], titles[right]))
        for left, right in (("prose.txt", "copy.txt"), ("long.txt", "near.txt"))
        if left in titles and right in titles
    }
    assert expected
    assert expected <= pairs


def test_manifest_rejects_a_tampered_group_batch(tmp_path: Path) -> None:
    run = run_chain(
        tmp_path,
        fixtures={"a.txt": "Odin dva tri " * 40, "b.txt": "Odin dva tri " * 40 + "."},
    )
    manifest = run.manifest(run.dedupe)
    parquet = next(Path(str(_summary(run)["roots"]["duplicate-groups"])).glob("part-*.parquet"))
    parquet.write_bytes(parquet.read_bytes() + b"\x00")
    with pytest.raises(ValueError, match="checksum"):
        validate_manifest(manifest, hash_file(manifest)[0])

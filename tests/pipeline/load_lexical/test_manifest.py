"""Published lexical load manifests must rehash, match, and reconcile before reuse."""

import json
from pathlib import Path
from typing import Any

import pytest

from arxiv_int.pipeline.load_lexical.artifacts import (
    DATASET,
    SCHEMA,
    manifest_path,
    validate_manifest,
)
from arxiv_int.pipeline.load_lexical.loader import LoadCounts
from arxiv_int.pipeline.load_lexical.publish import load_summary, publish_summary
from arxiv_int.pipeline.load_lexical.reconcile import FULL_SCOPE, Reconciliation
from arxiv_int.pipeline.load_lexical.reuse import validate_load_lexical_output
from arxiv_int.stores.projections.adapters.lexical import (
    INDEXED_COLUMNS,
    TOKENIZER_FINGERPRINT,
)
from arxiv_int.stores.projections.model import KIND_LEXICAL, KindBuild

GENERATION = "run-abc"
BUILD = KindBuild(
    kind=KIND_LEXICAL,
    projection_id="lexical:run_abc",
    version_id="run_abc",
    status="validated",
    engine="paradedb",
    engine_object="search.lexical_p_run_abc:lexical_p_run_abc_bm25",
    row_count=10,
    checksum="chunk-checksum",
    quality_status="pass",
    publishable=True,
    logical_ids=(),
    detail="",
)


def _summary(*, ok: bool = True) -> dict[str, Any]:
    reconciliation = Reconciliation(
        canonical_documents=4,
        canonical_chunks=10,
        projection_rows=10 if ok else 9,
        unindexed_chunks=0 if ok else 1,
        checksum_scope=FULL_SCOPE,
        checksum_match=True,
        detail="reconciled" if ok else "drifted",
    )
    return load_summary(
        generation_id=GENERATION,
        build=BUILD,
        loads=(LoadCounts("chunks", "corpus.chunks", 10, 1, "chunk-checksum"),),
        reconciliation=reconciliation,
        upstream={"chunking": {"manifest": "/tmp/chunk.json", "sha256": "digest"}},
        index_bytes={"index_bytes": 2048, "table_bytes": 4096},
        activated=True,
    )


def _attempt(directory: Path, manifest: Path, digest: str, *, generation: str = GENERATION) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "stage.json").write_text(
        json.dumps(
            {
                "stage": "load-lexical",
                "outcome": "produced",
                "outputs": [
                    {
                        "dataset": DATASET,
                        "generationId": generation,
                        "contractVersion": "1.0.0",
                        "partition": {"manifest": str(manifest), "sha256": digest},
                    }
                ],
            }
        ),
        encoding="ascii",
    )
    return directory


def test_summary_records_index_identity_and_load_evidence() -> None:
    summary = _summary()
    assert summary["schema"] == SCHEMA
    assert summary["index"]["indexed_columns"] == list(INDEXED_COLUMNS)
    assert summary["index"]["tokenizer_fingerprint"] == TOKENIZER_FINGERPRINT
    assert summary["index"]["index_bytes"] == 2048
    assert summary["projection"]["checksum"] == "chunk-checksum"
    assert summary["reconciliation"]["ok"] is True


def test_published_manifest_lands_under_the_run_search_root(tmp_path: Path) -> None:
    path, digest = publish_summary(tmp_path, GENERATION, _summary())
    assert path == manifest_path(tmp_path, GENERATION)
    assert path.parent.name == "search"
    assert validate_manifest(path, digest)["generation_id"] == GENERATION


def test_tampered_manifest_and_wrong_schema_refuse(tmp_path: Path) -> None:
    path, digest = publish_summary(tmp_path, GENERATION, _summary())
    path.write_text(path.read_text(encoding="ascii") + " ", encoding="ascii")
    with pytest.raises(ValueError, match="identity mismatch"):
        validate_manifest(path, digest)
    other = tmp_path / "other.json"
    other.write_text(json.dumps({"schema": "wrong"}), encoding="ascii")
    from arxiv_int.pipeline.control.artifacts import hash_file

    with pytest.raises(ValueError, match="unexpected lexical load manifest schema"):
        validate_manifest(other, hash_file(other)[0])


def test_reuse_validator_accepts_a_reconciled_attempt(tmp_path: Path) -> None:
    path, digest = publish_summary(tmp_path / "runs", GENERATION, _summary())
    validate_load_lexical_output(_attempt(tmp_path / "attempt", path, digest))


def test_reuse_validator_refuses_drifted_generation_and_reconciliation(tmp_path: Path) -> None:
    path, digest = publish_summary(tmp_path / "runs", GENERATION, _summary())
    directory = _attempt(tmp_path / "wrong-generation", path, digest, generation="run-other")
    with pytest.raises(ValueError, match="generation mismatch"):
        validate_load_lexical_output(directory)
    failed, failed_digest = publish_summary(tmp_path / "bad", GENERATION, _summary(ok=False))
    with pytest.raises(ValueError, match="did not reconcile"):
        validate_load_lexical_output(_attempt(tmp_path / "bad-attempt", failed, failed_digest))


def test_reuse_validator_ignores_other_stages(tmp_path: Path) -> None:
    directory = tmp_path / "chunk"
    directory.mkdir()
    (directory / "stage.json").write_text(
        json.dumps({"stage": "chunk", "outputs": []}), encoding="ascii"
    )
    validate_load_lexical_output(directory)

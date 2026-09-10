"""Ordinary corpus DAG proof publication, no-op replay and immutable verification."""

import os
from pathlib import Path

import pytest

from arxiv_int.evaluation.bundles.errors import BundleIntegrityError
from arxiv_int.evaluation.evaluate.errors import ProofIntegrityError, ProofStaleError
from arxiv_int.evaluation.proof.corpus_check import check_corpus_proof
from arxiv_int.evaluation.proof.corpus_publish import publish_corpus_proof
from arxiv_int.evaluation.proof.ops import publish_capability_proof
from arxiv_int.inference.scheduler.resources import HostSnapshot, RamSnapshot
from arxiv_int.pipeline.commands import create_run_context, run_dag
from arxiv_int.pipeline.dag.stages import production_registry
from arxiv_int.pipeline.forecast.commands import forecast_or_refuse
from arxiv_int.pipeline.run.persist import load_json
from arxiv_int.runtime import load_runtime_config
from arxiv_int.runtime.filesystem import FilesystemEvidence


def test_corpus_publish_verify_and_refuse_corrupt_or_stale_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in tuple(os.environ):
        if name.startswith(("ARCHIVE_SILO_", "PG_TABLESPACE_")):
            monkeypatch.delenv(name)
    for name in (
        "ARCHIVE_DIR",
        "RESULTS_DIR",
        "RUNS_DIR",
        "PGDATA_DIR",
        "PG_WAL_DIR",
        "SERVICE_STATE_DIR",
        "MODEL_CACHE_DIR",
        "TMP_DIR",
        "DATA_DIR",
    ):
        path = tmp_path / name.lower()
        path.mkdir()
        monkeypatch.setenv(name, str(path))
    archive = Path(os.environ["ARCHIVE_DIR"])
    (archive / "one.txt").write_bytes(
        b"Header\r\n\r\nSynthetic contract body. Delivery is complete.\r\n"
    )
    (archive / "copy.txt").write_bytes((archive / "one.txt").read_bytes())
    monkeypatch.setattr(
        "arxiv_int.extraction.tools.extraction_tool_versions", lambda: {"test": "1"}
    )
    monkeypatch.setattr(
        "arxiv_int.pipeline.forecast.devices.inspect_filesystem",
        lambda path: FilesystemEvidence(path, "ext4", "8:1", False, 10**18, True, False),
    )
    monkeypatch.setattr(
        "arxiv_int.pipeline.forecast.collect.snapshot_host",
        lambda **kwargs: HostSnapshot(RamSnapshot(64, 48), ()),
    )
    context = create_run_context(project_root=Path.cwd(), to_stage="chunk")
    config = load_runtime_config(project_root=Path.cwd())
    registry = production_registry()
    forecast_or_refuse(context, config, registry)
    assert run_dag(context, registry) == 0
    result = publish_capability_proof(
        capability="corpus-foundation",
        project_root=Path.cwd(),
        run_id=context.run_id,
        proof_id="synthetic-proof",
        results_dir=context.results_dir,
        runs_dir=context.runs_dir,
    )
    assert result.directory.name == "synthetic-proof"
    report = load_json(result.directory / "report.json")
    assert report["metrics"]["accounting"]["occurrences"] == 2
    assert report["metrics"]["accounting"]["documents"] == 1
    assert report["noop_worker_invocations"] == 0
    assert all(row["cache_hit"] for row in report["replay"])
    assert check_corpus_proof(result.directory, Path.cwd()) == result.fingerprint
    with pytest.raises(ProofIntegrityError, match="already exists"):
        publish_corpus_proof(
            project_root=Path.cwd(),
            run_id=context.run_id,
            proof_id="synthetic-proof",
            results_dir=context.results_dir,
            runs_dir=context.runs_dir,
        )
    weights = config.model_cache_dir / "docling" / "weights.bin"
    weights.parent.mkdir()
    weights.write_bytes(b"new-model")
    with pytest.raises(ProofStaleError):
        check_corpus_proof(result.directory, Path.cwd())
    weights.unlink()
    weights.parent.rmdir()
    artifact = next(context.results_dir.rglob("*.parquet"))
    original = artifact.read_bytes()
    artifact.write_bytes(original + b"corrupt")
    with pytest.raises(ProofIntegrityError, match="external corpus artifact"):
        check_corpus_proof(result.directory, Path.cwd())
    artifact.write_bytes(original)
    report_path = result.directory / "report.json"
    report_path.write_bytes(report_path.read_bytes() + b" ")
    with pytest.raises(BundleIntegrityError):
        check_corpus_proof(result.directory, Path.cwd())

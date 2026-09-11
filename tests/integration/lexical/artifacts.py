"""Validate ordinary lexical load artifacts and write path-free test logs."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.pipeline.control.artifacts import hash_file, validate_attempt
from arxiv_int.pipeline.load_lexical.artifacts import DATASET, validate_manifest
from arxiv_int.pipeline.load_lexical.reconcile import Reconciliation, reconcile
from arxiv_int.pipeline.load_lexical.reuse import validate_load_lexical_output
from arxiv_int.pipeline.quality.evidence import validate_quality_evidence
from arxiv_int.pipeline.run.persist import StageExecution, load_json
from arxiv_int.retrieval.projection import LexicalTarget
from tests.integration.corpus.artifacts import require

STAGE = "load-lexical"


def validate_lexical_execution(item: StageExecution) -> dict[str, Any]:
    """Recheck the load-lexical attempt, quality evidence, and published manifest."""
    require(item.stage == STAGE, "expected the load-lexical execution")
    require(item.status in {"succeeded", "quarantined"}, "load-lexical did not succeed")
    require(item.outcome in {"produced", "empty"}, "load-lexical is partial or failed")
    directory = Path(item.directory or "")
    validate_attempt(directory, reuse_key=item.reuse_key, attempt=item.attempt)
    payload = load_json(directory / "stage.json")
    outputs = payload["outputs"]
    require(bool(outputs) and outputs[0]["dataset"] == DATASET, "missing lexical load outputs")
    generation = outputs[0]["generationId"]
    require(
        validate_quality_evidence(directory, generation), "load-lexical quality evidence failed"
    )
    validate_load_lexical_output(directory)
    pointer = outputs[0]["partition"]
    path = Path(pointer["manifest"])
    summary = validate_manifest(path, pointer["sha256"])
    require(summary["reconciliation"]["ok"], "published lexical reconciliation failed")
    require(summary["activated"] is True, "lexical projection was not activated")
    return {"digest": pointer["sha256"], "path": path, "summary": summary}


def live_reconciliation(
    connection: Any, target: LexicalTarget, summary: Mapping[str, Any]
) -> Reconciliation:
    """Reconcile the active covering table against the published load counts."""
    chunks = next(item for item in summary["loads"] if item["contract"] == "chunks")
    result = reconcile(
        connection,
        table=target.table,
        loaded_chunks=int(chunks["rows"]),
        loaded_checksum=str(chunks["checksum"]),
        projection_checksum=str(summary["projection"]["checksum"]),
    )
    require(result.ok, result.detail)
    require(result.canonical_chunks > 0, "canonical chunk table is empty")
    require(target.row_count == result.projection_rows, "active pointer row count drifted")
    require(
        result.as_json_dict()["projectionRows"] == summary["reconciliation"]["projectionRows"],
        "live projection count does not match the published manifest",
    )
    return result


def write_integration_log(data_dir: Path, payload: Mapping[str, Any]) -> Path:
    """Write one ASCII JSON summary under ``$DATA_DIR/integration/lexical-retrieval/``."""
    directory = data_dir / "integration" / "lexical-retrieval"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{payload['runId']}.json"
    path.write_text(normalize_json(dict(payload)), encoding="ascii")
    digest, _size = hash_file(path)
    sidecar = directory / f"{payload['runId']}.sha256"
    sidecar.write_text(f"{digest}\n", encoding="ascii")
    return path

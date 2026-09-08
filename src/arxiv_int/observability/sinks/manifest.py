"""Final per-stage observability manifest written beside run logs."""

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.observability.logging.redact import redact_mapping, redact_text
from arxiv_int.observability.metrics.constants import MANIFEST_NAME, SCHEMA_ID
from arxiv_int.observability.metrics.events import ProgressSnapshot


def build_stage_manifest(
    snapshot: ProgressSnapshot,
    *,
    outcome: str,
    next_action: str,
    warning_codes: tuple[str, ...] = (),
    error_codes: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Return a secret-free final stage summary for logs and dashboards."""
    payload: dict[str, Any] = {
        "bytes": snapshot.bytes,
        "elapsed_seconds": snapshot.elapsed_seconds,
        "error_codes": list(error_codes),
        "errors": snapshot.errors,
        "event": "stage-manifest",
        "next_action": redact_text(next_action),
        "outcome": outcome,
        "processed": snapshot.processed,
        "remaining": snapshot.remaining,
        "resources": snapshot.resources.as_dict(),
        "run_id": snapshot.run_id,
        "schema": SCHEMA_ID,
        "shard": snapshot.shard_token,
        "stage": snapshot.stage,
        "throughput_per_s": snapshot.throughput_per_s,
        "ts": snapshot.ts,
        "warning_codes": list(warning_codes),
        "worker_state": snapshot.worker_state,
    }
    return redact_mapping(payload)


def write_stage_manifest(run_dir: Path, payload: Mapping[str, Any]) -> Path:
    """Atomically write ``observability-manifest.json`` under the run logs directory."""
    directory = run_dir / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / MANIFEST_NAME
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(normalize_json(payload) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path

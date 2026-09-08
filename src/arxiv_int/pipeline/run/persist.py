"""JSON persistence for run context and stage status."""

import json
import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.run.context import RunContext

CONTEXT_NAME = "run-context.json"
STATUS_NAME = "status.json"
PRUNE_DIR = "prune-plans"


@dataclass(frozen=True, slots=True)
class StageExecution:
    """One planned or completed stage in a run."""

    stage: str
    shard_id: str
    status: str
    cache_hit: bool
    skipped: bool
    reuse_key: str
    directory: str | None
    attempt: int
    detail: str
    worker_invoked: bool
    bytes: int
    outcome: str


@dataclass(frozen=True, slots=True)
class RunStatus:
    """Persisted DAG walk for one run id."""

    run_id: str
    generation_id: str
    halted: bool
    halt_reason: str
    executions: tuple[StageExecution, ...]
    lineage: tuple[tuple[str, str], ...]
    not_selected: tuple[str, ...]


def run_dir(runs_dir: Path, run_id: str) -> Path:
    """Return ``$RUNS_DIR/<run-id>/``."""
    return runs_dir / run_id


def write_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Atomically replace a JSON document with sorted keys."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(normalize_json(payload), encoding="utf-8")
    os.replace(tmp, path)


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object."""
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"{path} is not a JSON object")
    return loaded


def save_context(context: RunContext) -> Path:
    """Write frozen run context under the run directory."""
    path = run_dir(context.runs_dir, context.run_id) / CONTEXT_NAME
    write_json(
        path,
        {
            "run_id": context.run_id,
            "generation_id": context.generation_id,
            "profile": context.profile,
            "config_fingerprint": context.config_fingerprint,
            "source_snapshot": context.source_snapshot,
            "silos": [{"silo_id": silo.silo_id, "root": str(silo.root)} for silo in context.silos],
            "results_dir": str(context.results_dir),
            "runs_dir": str(context.runs_dir),
            "project_root": str(context.project_root),
            "secret_free": dict(context.secret_free),
            "parameters": dict(context.parameters),
            "from_stage": context.from_stage,
            "to_stage": context.to_stage,
        },
    )
    return path


def load_context(runs_dir: Path, run_id: str) -> RunContext:
    """Load a previously frozen run context."""
    payload = load_json(run_dir(runs_dir, run_id) / CONTEXT_NAME)
    silos = tuple(
        SiloRoot(str(item["silo_id"]), Path(str(item["root"]))) for item in payload["silos"]
    )
    return RunContext(
        run_id=str(payload["run_id"]),
        generation_id=str(payload["generation_id"]),
        profile=str(payload["profile"]),
        config_fingerprint=str(payload["config_fingerprint"]),
        source_snapshot=str(payload["source_snapshot"]),
        silos=silos,
        results_dir=Path(str(payload["results_dir"])),
        runs_dir=Path(str(payload["runs_dir"])),
        project_root=Path(str(payload["project_root"])),
        secret_free=dict(payload["secret_free"]),
        parameters=dict(payload["parameters"]),
        from_stage=payload.get("from_stage"),
        to_stage=payload.get("to_stage"),
    )


def save_status(runs_dir: Path, status: RunStatus) -> Path:
    """Write the DAG walk for one run."""
    path = run_dir(runs_dir, status.run_id) / STATUS_NAME
    write_json(path, _status_payload(status))
    return path


def load_status(runs_dir: Path, run_id: str) -> RunStatus:
    """Load a persisted DAG walk."""
    payload = load_json(run_dir(runs_dir, run_id) / STATUS_NAME)
    executions = tuple(_execution_from_payload(item) for item in payload["executions"])
    lineage = tuple((str(left), str(right)) for left, right in payload["lineage"])
    return RunStatus(
        str(payload["run_id"]),
        str(payload["generation_id"]),
        bool(payload["halted"]),
        str(payload["halt_reason"]),
        executions,
        lineage,
        tuple(str(name) for name in payload["not_selected"]),
    )


def _status_payload(status: RunStatus) -> dict[str, Any]:
    return {
        "run_id": status.run_id,
        "generation_id": status.generation_id,
        "halted": status.halted,
        "halt_reason": status.halt_reason,
        "executions": [
            {
                "stage": item.stage,
                "shard_id": item.shard_id,
                "status": item.status,
                "cache_hit": item.cache_hit,
                "skipped": item.skipped,
                "reuse_key": item.reuse_key,
                "directory": item.directory,
                "attempt": item.attempt,
                "detail": item.detail,
                "worker_invoked": item.worker_invoked,
                "bytes": item.bytes,
                "outcome": item.outcome,
            }
            for item in status.executions
        ],
        "lineage": [list(edge) for edge in status.lineage],
        "not_selected": list(status.not_selected),
    }


def _execution_from_payload(item: Mapping[str, Any]) -> StageExecution:
    directory = item.get("directory")
    return StageExecution(
        str(item["stage"]),
        str(item.get("shard_id") or "default"),
        str(item["status"]),
        bool(item["cache_hit"]),
        bool(item["skipped"]),
        str(item["reuse_key"]),
        None if directory is None else str(directory),
        int(item["attempt"]),
        str(item["detail"]),
        bool(item["worker_invoked"]),
        int(item["bytes"]),
        str(item["outcome"]),
    )

"""Require measured timing and resource evidence for every corpus stage."""

import json
import math
from typing import Any

from arxiv_int.evaluation.proof.corpus_artifacts import STAGES, require

_FIELDS = ("elapsed_seconds", "cpu_pct", "ram_available_gib", "disk_free_gib")


def resource_summary(payload: bytes) -> dict[str, dict[str, float]]:
    """Summarize retained samples, refusing absent, nonfinite or incomplete stage evidence."""
    rows: list[dict[str, Any]] = [json.loads(line) for line in payload.splitlines() if line.strip()]
    return {stage: _stage_summary(rows, stage) for stage in STAGES}


def _stage_summary(rows: list[dict[str, Any]], stage: str) -> dict[str, float]:
    selected = [row for row in rows if row.get("stage") == stage]
    require(bool(selected), f"missing resource evidence for {stage}")
    require(
        any(row.get("worker_state") == "completed" for row in selected),
        f"missing completed timing for {stage}",
    )
    for row in selected:
        require(
            all(_measurement(row.get(name)) for name in _FIELDS),
            f"invalid resource measurement for {stage}",
        )
    return {
        "max_elapsed_seconds": max(float(row["elapsed_seconds"]) for row in selected),
        "max_sampled_cpu_pct": max(float(row["cpu_pct"]) for row in selected),
        "min_sampled_ram_available_gib": min(float(row["ram_available_gib"]) for row in selected),
        "min_sampled_disk_free_gib": min(float(row["disk_free_gib"]) for row in selected),
    }


def _measurement(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )

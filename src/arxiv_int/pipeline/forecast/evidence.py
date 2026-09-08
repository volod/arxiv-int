"""Cache-hit plans and comparable prior-run telemetry."""

import json
from pathlib import Path

from arxiv_int.pipeline.context import RunContext
from arxiv_int.pipeline.control.fingerprints import reuse_key
from arxiv_int.pipeline.execute import stage_identity, try_reuse
from arxiv_int.pipeline.forecast.inputs import CacheHitPlan, ComparableRun
from arxiv_int.pipeline.persist import load_json
from arxiv_int.pipeline.reconcile.scan import bind_shard, source_shard_ids
from arxiv_int.pipeline.registry import StageRegistry
from arxiv_int.pipeline.reuse_index import ReuseEntry, load_reuse_index

_MANIFEST = "observability-manifest.json"


def cache_plan(
    context: RunContext,
    registry: StageRegistry,
    plan: tuple[str, ...],
    *,
    force: bool = False,
) -> CacheHitPlan:
    """Mark stages whose reuse keys still validate as cache hits."""
    index = load_reuse_index(context.runs_dir)
    shards = source_shard_ids(context)
    shard_keys: dict[str, dict[str, str]] = {shard_id: {} for shard_id in shards}
    hits = tuple(
        _stage_cache(name, context, registry, index, shards, shard_keys, force) for name in plan
    )
    return CacheHitPlan(hits)


def _stage_cache(
    name: str,
    context: RunContext,
    registry: StageRegistry,
    index: dict[str, ReuseEntry],
    shards: tuple[str, ...],
    shard_keys: dict[str, dict[str, str]],
    force: bool,
) -> tuple[str, bool, int]:
    spec = registry.get(name)
    cached_all = True
    size = 0
    for shard_id in shards:
        bound = bind_shard(context, shard_id)
        upstream = tuple(
            shard_keys[shard_id][item] for item in spec.depends_on if item in shard_keys[shard_id]
        )
        key = reuse_key(stage_identity(spec, bound, upstream))
        reused = try_reuse(index.get(key), force=force)
        if reused is None:
            cached_all = False
        else:
            size += reused.bytes
        shard_keys[shard_id][name] = key
    return name, cached_all, size


def load_comparable_runs(
    runs_dir: Path,
    *,
    profile: str,
    current_id: str | None = None,
) -> tuple[ComparableRun, ...]:
    """Read prior stage manifests; skip the in-progress forecast id."""
    found: list[ComparableRun] = []
    if not runs_dir.is_dir():
        return ()
    for child in sorted(runs_dir.iterdir()):
        if not child.is_dir() or child.name == current_id:
            continue
        manifest = child / "logs" / _MANIFEST
        context_path = child / "run-context.json"
        if not manifest.is_file() or not context_path.is_file():
            continue
        try:
            stored = load_json(context_path)
            payload = load_json(manifest)
        except (OSError, ValueError):
            continue
        if str(stored.get("profile", "")) != profile:
            continue
        found.append(_from_manifest(child.name, profile, payload, child))
    return tuple(found)


def _from_manifest(
    run_id: str, profile: str, payload: dict[str, object], run_dir: Path
) -> ComparableRun:
    stage = str(payload.get("stage", ""))
    seconds = _as_float(payload.get("elapsed_seconds", 0))
    size = _as_int(payload.get("bytes", 0))
    stage_seconds = {stage: seconds} if stage else {}
    stage_bytes = {stage: size} if stage else {}
    progress = run_dir / "logs" / "progress.jsonl"
    if progress.is_file():
        stage_seconds, stage_bytes = _from_progress(progress, stage_seconds, stage_bytes)
    input_bytes = _as_int(payload.get("bytes", 0))
    status = run_dir / "status.json"
    if status.is_file():
        try:
            loaded = load_json(status)
            input_bytes = sum(int(item.get("bytes", 0)) for item in loaded.get("executions", ()))
        except (OSError, TypeError, ValueError):
            pass
    return ComparableRun(run_id, profile, max(input_bytes, 1), stage_seconds, stage_bytes)


def _from_progress(
    path: Path,
    seconds: dict[str, float],
    sizes: dict[str, int],
) -> tuple[dict[str, float], dict[str, int]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return seconds, sizes
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except ValueError:
            continue
        if not isinstance(payload, dict):
            continue
        stage = str(payload.get("stage", ""))
        if not stage:
            continue
        elapsed = _as_float(payload.get("elapsed_seconds", 0))
        size = _as_int(payload.get("bytes", 0))
        if elapsed > seconds.get(stage, 0):
            seconds[stage] = elapsed
        if size > sizes.get(stage, 0):
            sizes[stage] = size
    return seconds, sizes


def _as_float(value: object) -> float:
    if isinstance(value, bool) or value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return 0.0
    return 0.0


def _as_int(value: object) -> int:
    if isinstance(value, bool) or value is None:
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0

"""Run one registered stage through the shard executor and reuse index."""

import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.interfaces.pipeline import StageContext, StageResult
from arxiv_int.pipeline.control.artifacts import ArtifactPublishError, validate_attempt
from arxiv_int.pipeline.control.executor import ShardDecision, ShardExecutor
from arxiv_int.pipeline.control.fingerprints import ReuseIdentity, reuse_key
from arxiv_int.pipeline.control.model import ShardWork
from arxiv_int.pipeline.control.owned import owned_fingerprints
from arxiv_int.pipeline.control.quality import activation_decision
from arxiv_int.pipeline.dag.registry import StageRegistry, StageSpec
from arxiv_int.pipeline.quality.bound import QualityBoundary, apply_boundary
from arxiv_int.pipeline.run.context import RunContext
from arxiv_int.pipeline.run.errors import QualityBoundaryError, UnregisteredStageError
from arxiv_int.pipeline.run.persist import StageExecution
from arxiv_int.pipeline.run.reuse_index import ReuseEntry

UPSTREAM_POINTERS: Mapping[str, str] = {
    "source-occurrences": "inventory",
    "documents": "extraction",
    "normalized-documents": "normalization",
    "duplicate-groups": "dedupe",
    "chunks": "chunking",
}


def stage_context(context: RunContext, stage: str) -> StageContext:
    """Build the typed stage context from a frozen run."""
    options = dict(context.parameters)
    options["project_root"] = str(context.project_root)
    options["source_drift_policy"] = context.source_drift_policy
    options["source_metadata_snapshot"] = context.source_metadata_snapshot or ""
    options["tmp_dir"] = context.secret_free.get("TMP_DIR", str(context.results_dir / "tmp"))
    options["model_cache_dir"] = context.secret_free.get(
        "MODEL_CACHE_DIR", str(context.results_dir / "models")
    )
    options["protected_roots"] = json.dumps(
        [
            value
            for key, value in context.secret_free.items()
            if key in {"PGDATA_DIR", "PG_WAL_DIR"} or key.startswith("PG_TABLESPACE_")
            if value
        ]
    )
    return StageContext(
        stage,
        context.run_id,
        context.generation_id,
        context.silos,
        context.results_dir,
        options,
    )


def stage_identity(
    spec: StageSpec, context: RunContext, upstream_keys: tuple[str, ...]
) -> ReuseIdentity:
    """Bind one stage shard to frozen configuration and upstream reuse keys."""
    shard_id = context.parameters.get("document_id", "default")
    inputs: tuple[str, ...]
    if not spec.depends_on:
        inputs = (shard_id,) if shard_id != "default" else (context.source_snapshot,)
    else:
        inputs = upstream_keys or ("none",)
    return ReuseIdentity(
        spec.name,
        spec.version,
        shard_id,
        dict(context.parameters) or {"none": "none"},
        inputs,
        upstream_keys,
        owned_fingerprints(spec, context.project_root, context.config_fingerprint),
    )


def try_reuse(entry: ReuseEntry | None, *, force: bool) -> StageExecution | None:
    """Return a cache hit when the indexed attempt still validates."""
    if force or entry is None or entry.stale or entry.status not in {"succeeded", "quarantined"}:
        return None
    directory = Path(entry.directory)
    try:
        validate_attempt(directory, reuse_key=entry.reuse_key, attempt=entry.attempt)
        for validate in _output_validators():
            validate(directory)
    except (ArtifactPublishError, OSError, ValueError, KeyError, TypeError):
        return None
    if load_stage_outcome(directory) not in {"produced", "empty"}:
        return None
    from arxiv_int.pipeline.quality.evidence import validate_quality_evidence

    if not validate_quality_evidence(directory, entry.generation_id):
        return None
    return StageExecution(
        entry.stage,
        entry.shard_id,
        entry.status,
        True,
        True,
        entry.reuse_key,
        entry.directory,
        entry.attempt,
        "cache hit after manifest validation",
        False,
        entry.bytes,
        load_stage_outcome(directory),
    )


def _output_validators() -> tuple[Callable[[Path], None], ...]:
    """Return every producer-owned validator that guards one cached attempt."""
    from arxiv_int.extraction.reuse import validate_extraction_output
    from arxiv_int.pipeline.chunk.reuse import validate_chunk_output
    from arxiv_int.pipeline.dedupe.reuse import validate_dedupe_output
    from arxiv_int.pipeline.inventory.reuse import validate_inventory_output
    from arxiv_int.pipeline.normalize.reuse import validate_normalization_output

    return (
        validate_inventory_output,
        validate_extraction_output,
        validate_normalization_output,
        validate_dedupe_output,
        validate_chunk_output,
    )


def encode_result(result: StageResult) -> bytes:
    """Serialize one stage result as a published sibling payload."""
    payload = {
        "detail": result.detail,
        "outcome": result.outcome,
        "outputs": [
            {
                "contractVersion": item.contract_version,
                "dataset": item.dataset,
                "generationId": item.generation_id,
                "partition": dict(item.partition),
            }
            for item in result.outputs
        ],
        "stage": result.stage,
    }
    return normalize_json(payload).encode("utf-8")


def execute_stage(
    registry: StageRegistry,
    executor: ShardExecutor,
    quality: QualityBoundary,
    context: RunContext,
    name: str,
    upstream_keys: tuple[str, ...],
    index: Mapping[str, ReuseEntry],
    *,
    force: bool = False,
) -> StageExecution:
    """Reuse a valid attempt or run the registered worker into a new attempt."""
    spec = registry.get(name)
    runner = spec.runner
    if runner is None:
        raise UnregisteredStageError((name,))
    identity = stage_identity(spec, context, upstream_keys)
    key = reuse_key(identity)
    eligible = activation_decision(quality.checks(), generation_id=context.generation_id).allowed
    reused = try_reuse(index.get(key), force=force or not eligible)
    if reused is not None:
        return reused
    work = ShardWork(
        context.run_id,
        context.generation_id,
        spec.name,
        spec.version,
        identity.shard_id,
        context.config_fingerprint,
        identity,
        checks=quality.checks(),
        row_counts={"stage.json": 1},
    )

    def worker(_directory: Path) -> Mapping[str, bytes]:
        from dataclasses import replace

        scoped = stage_context(context, spec.name)
        scoped = replace(
            scoped,
            options={
                **scoped.options,
                **_upstream_options(upstream_keys, index),
                "producer_identity": key,
            },
        )
        result = runner.run(scoped)
        if result.stage != spec.name or any(
            item.generation_id != context.generation_id for item in result.outputs
        ):
            raise QualityBoundaryError("stage output identity mismatch")
        if result.outcome == "failed":
            raise RuntimeError(result.detail)
        files = {"stage.json": encode_result(result)}
        files["quality.json"] = apply_boundary(
            spec,
            files,
            quality,
            generation_id=context.generation_id,
            run_id=context.run_id,
            result=result,
        )
        return files

    return _from_decision(
        spec.name, identity.shard_id, key, executor.execute(work, worker, force=force)
    )


def _upstream_options(
    upstream_keys: tuple[str, ...], index: Mapping[str, ReuseEntry]
) -> dict[str, str]:
    """Expose validated upstream artifact pointers to dependent stage runners."""
    options: dict[str, str] = {}
    for key in upstream_keys:
        entry = index.get(key)
        if entry is None:
            continue
        payload: Any = json.loads(
            (Path(entry.directory) / "stage.json").read_text(encoding="utf-8")
        )
        for output in payload.get("outputs", []) if isinstance(payload, dict) else ():
            if not isinstance(output, dict):
                continue
            pointer = UPSTREAM_POINTERS.get(str(output.get("dataset")))
            partition = output.get("partition")
            if pointer is None or not isinstance(partition, dict):
                continue
            options[f"{pointer}_manifest"] = str(partition.get("manifest", ""))
            options[f"{pointer}_manifest_sha256"] = str(partition.get("sha256", ""))
    return options


def execution_to_entry(
    context: RunContext, execution: StageExecution, shard_id: str
) -> ReuseEntry | None:
    """Index a successful attempt for later cache hits."""
    if execution.directory is None or execution.status not in {"succeeded", "quarantined"}:
        return None
    return ReuseEntry(
        execution.reuse_key,
        execution.stage,
        shard_id,
        execution.attempt,
        execution.directory,
        execution.status,
        execution.bytes,
        Path(execution.directory).parents[3].name if execution.cache_hit else context.run_id,
        _producer_generation(Path(execution.directory)),
        False,
    )


def _producer_generation(directory: Path) -> str:
    payload = json.loads((directory / "quality.json").read_text(encoding="ascii"))
    return str(payload["generation_id"])


def load_stage_outcome(directory: Path | None) -> str:
    """Read the honest stage outcome from a published attempt payload."""
    if directory is None:
        return "failed"
    path = directory / "stage.json"
    if not path.is_file():
        return "failed"
    try:
        payload: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "failed"
    if not isinstance(payload, dict):
        return "failed"
    outcome = str(payload.get("outcome", "failed"))
    if outcome in {"produced", "partial", "empty", "failed", "not-selected"}:
        return outcome
    return "failed"


def _from_decision(stage: str, shard_id: str, key: str, decision: ShardDecision) -> StageExecution:
    directory = decision.directory
    path = None if directory is None else str(directory)
    outcome = load_stage_outcome(directory)
    if decision.status not in {"succeeded", "quarantined"}:
        outcome = "failed"
    return StageExecution(
        stage,
        shard_id,
        decision.status,
        decision.cache_hit,
        decision.cache_hit,
        key,
        path,
        decision.attempt,
        decision.detail,
        decision.worker_invoked,
        _payload_bytes(directory),
        outcome,
    )


def _payload_bytes(directory: Path | None) -> int:
    if directory is None:
        return 0
    payload = directory / "stage.json"
    if not payload.is_file():
        return 0
    return payload.stat().st_size

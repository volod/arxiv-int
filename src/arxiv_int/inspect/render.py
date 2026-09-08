"""Secret-free console and JSON rendering for inspection summaries."""

from collections.abc import Iterable, Mapping
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.inspect.model import (
    InspectionSummary,
    LineageSummary,
    PartitionSummary,
    QualityRuleSummary,
    StageSummary,
)
from arxiv_int.observability.redact import extra_secrets_from_env, redact_text

_BLOCKED = frozenset({"prompt", "text", "document", "body", "password", "secret", "token"})


def console_lines(summary: InspectionSummary) -> tuple[str, ...]:
    """Render ASCII operator lines with redacted details."""
    secrets = extra_secrets_from_env()
    lines = [
        f"schema={summary.schema}",
        f"kind={summary.kind}",
        f"target={summary.target}",
        f"run_id={summary.run_id or 'none'}",
        f"generation_id={summary.generation_id or 'none'}",
        f"profile={summary.profile or 'none'}",
        f"halted={str(summary.halted).lower()}",
    ]
    if summary.halt_reason:
        lines.append(f"halt_reason={_safe(summary.halt_reason, secrets)}")
    for stage in summary.stages:
        lines.extend(_stage_lines(stage, secrets))
    for part in summary.lake:
        lines.append(
            f"lake dataset={part.dataset} version={part.contract_version} "
            f"conformance={part.conformance} bytes={part.bytes} "
            f"rows={_count(part.row_count)}"
        )
    for check in summary.published_quality:
        lines.append(
            f"published_quality rule={check.rule_id} scope={check.scope} "
            f"status={check.status} failed={check.failed_count}"
        )
    for item in summary.published_lineage:
        lines.append(
            f"published_lineage command={item.command} status={item.status} "
            f"model={item.model_fingerprint}"
        )
    if summary.not_selected:
        lines.append("not_selected=" + ",".join(summary.not_selected))
    return tuple(lines)


def json_document(summary: InspectionSummary) -> str:
    """Return canonical redacted JSON for one inspection."""
    secrets = extra_secrets_from_env()
    payload = redact_tree(_payload(summary), secrets)
    return normalize_json(payload)


def _stage_lines(stage: StageSummary, secrets: Iterable[str]) -> list[str]:
    rows = sum(file.row_count or 0 for file in stage.files)
    lines = [
        (
            f"stage={stage.stage} status={stage.status} outcome={stage.outcome} "
            f"attempt={stage.attempt} cache_hit={str(stage.cache_hit).lower()} "
            f"bytes={stage.bytes} rows={rows} valid={str(stage.tree_valid).lower()} "
            f"schema_drifted={str(stage.schema_drifted).lower()} "
            f"directory={stage.directory}"
        )
    ]
    for part in stage.partitions:
        lines.append(
            f"  partition dataset={part.dataset} version={part.contract_version} "
            f"conformance={part.conformance}"
        )
    for check in stage.quality:
        lines.append(
            f"  quality rule={check.rule_id} scope={check.scope} "
            f"status={check.status} failed={check.failed_count}"
        )
    for item in stage.lineage:
        lines.append(
            f"  lineage command={item.command} status={item.status} model={item.model_fingerprint}"
        )
    for anchor in stage.anchors:
        lines.append(
            f"  anchor silo={anchor.silo_id} path={anchor.relative_path} kind={anchor.kind}"
        )
    for name in stage.quarantines:
        lines.append(f"  quarantine={name}")
    for detail in stage.failures:
        lines.append(f"  failure={_safe(detail, secrets)}")
    return lines


def _payload(summary: InspectionSummary) -> dict[str, Any]:
    return {
        "generation_id": summary.generation_id,
        "halt_reason": summary.halt_reason,
        "halted": summary.halted,
        "kind": summary.kind,
        "lake": [_partition(item) for item in summary.lake],
        "limit": summary.limit,
        "not_selected": list(summary.not_selected),
        "profile": summary.profile,
        "published_lineage": [_lineage(item) for item in summary.published_lineage],
        "published_quality": [_quality(item) for item in summary.published_quality],
        "run_id": summary.run_id,
        "schema": summary.schema,
        "stages": [_stage(item) for item in summary.stages],
        "target": summary.target,
    }


def _stage(stage: StageSummary) -> dict[str, Any]:
    return {
        "anchors": [
            {
                "cell_range": item.cell_range,
                "kind": item.kind,
                "page": item.page,
                "relative_path": item.relative_path,
                "scan_id": item.scan_id,
                "sheet": item.sheet,
                "silo_id": item.silo_id,
            }
            for item in stage.anchors
        ],
        "attempt": stage.attempt,
        "bytes": stage.bytes,
        "cache_hit": stage.cache_hit,
        "directory": stage.directory,
        "failures": list(stage.failures),
        "files": [
            {
                "bytes": item.bytes,
                "name": item.name,
                "row_count": item.row_count,
                "sha256": item.sha256,
                "valid": item.valid,
            }
            for item in stage.files
        ],
        "lineage": [_lineage(item) for item in stage.lineage],
        "outcome": stage.outcome,
        "partitions": [_partition(item) for item in stage.partitions],
        "quality": [_quality(item) for item in stage.quality],
        "quarantines": list(stage.quarantines),
        "schema_drifted": stage.schema_drifted,
        "shard_id": stage.shard_id,
        "stage": stage.stage,
        "status": stage.status,
        "tree_valid": stage.tree_valid,
    }


def _partition(item: PartitionSummary) -> dict[str, Any]:
    return {
        "bytes": item.bytes,
        "conformance": item.conformance,
        "contract_version": item.contract_version,
        "dataset": item.dataset,
        "generation_id": item.generation_id,
        "partition": [list(pair) for pair in item.partition],
        "row_count": item.row_count,
    }


def _quality(item: QualityRuleSummary) -> dict[str, Any]:
    return {
        "failed_count": item.failed_count,
        "required": item.required,
        "rule_id": item.rule_id,
        "scope": item.scope,
        "status": item.status,
    }


def _lineage(item: LineageSummary) -> dict[str, Any]:
    return {
        "activatable": item.activatable,
        "command": item.command,
        "input_fingerprint": item.input_fingerprint,
        "model_fingerprint": item.model_fingerprint,
        "status": item.status,
    }


def redact_tree(value: object, secrets: Iterable[str]) -> object:
    """Recursively redact strings and blocked keys."""
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if str(key).lower() in _BLOCKED:
                result[str(key)] = "<redacted>"
            else:
                result[str(key)] = redact_tree(item, secrets)
        return result
    if isinstance(value, list):
        return [redact_tree(item, secrets) for item in value]
    if isinstance(value, str):
        return _safe(value, secrets)
    return value


def _safe(text: str, secrets: Iterable[str]) -> str:
    return redact_text(text, secrets)


def _count(value: int | None) -> str:
    return "unknown" if value is None else str(value)

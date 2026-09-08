"""JSON codec for forecast decisions."""

from typing import Any

from arxiv_int.pipeline.forecast.model import (
    SCHEMA_ID,
    ByteRange,
    Coefficient,
    DeviceBudget,
    ForecastDocument,
    HostAssumptions,
    OutputCosts,
    StageForecast,
    TimeRange,
    WorkCounts,
)


def document_payload(document: ForecastDocument) -> dict[str, Any]:
    """Serialize a forecast decision with sorted keys at dump time."""
    return {
        "actions": list(document.actions),
        "coefficients": [_coefficient(item) for item in document.coefficients],
        "confidence": document.confidence,
        "config_fingerprint": document.config_fingerprint,
        "critical_path": list(document.critical_path),
        "decision": document.decision,
        "devices": [_device(item) for item in document.devices],
        "envelope_fingerprint": document.envelope_fingerprint,
        "excluded": list(document.excluded),
        "fingerprint": document.fingerprint,
        "forecast_id": document.forecast_id,
        "host": _host(document.host),
        "inventory_source": document.inventory_source,
        "not_selected": list(document.not_selected),
        "outputs": _outputs(document.outputs),
        "plan": list(document.plan),
        "production": document.production,
        "profile": document.profile,
        "run_id": document.run_id,
        "schema": SCHEMA_ID,
        "source_snapshot": document.source_snapshot,
        "stages": [_stage(item) for item in document.stages],
        "time": _time(document.time),
    }


def _range(span: ByteRange) -> dict[str, int]:
    return {"lower": span.lower, "upper": span.upper}


def _time(span: TimeRange) -> dict[str, float]:
    return {"lower_seconds": span.lower_seconds, "upper_seconds": span.upper_seconds}


def _work(work: WorkCounts) -> dict[str, int]:
    return {
        "added": work.added,
        "cached": work.cached,
        "changed": work.changed,
        "input_bytes": work.input_bytes,
        "input_files": work.input_files,
        "recomputed": work.recomputed,
        "removed": work.removed,
        "renamed": work.renamed,
    }


def _outputs(outputs: OutputCosts) -> dict[str, dict[str, int]]:
    return {
        "artifacts": _range(outputs.artifacts),
        "backups": _range(outputs.backups),
        "database_heap": _range(outputs.database_heap),
        "graph": _range(outputs.graph),
        "indexes": _range(outputs.indexes),
        "logs": _range(outputs.logs),
        "normalized": _range(outputs.normalized),
        "rebuild": _range(outputs.rebuild),
        "rollback": _range(outputs.rollback),
        "staging": _range(outputs.staging),
        "temp": _range(outputs.temp),
        "vectors": _range(outputs.vectors),
        "wal": _range(outputs.wal),
    }


def _stage(item: StageForecast) -> dict[str, Any]:
    return {
        "actions": list(item.actions),
        "cache_hit": item.cache_hit,
        "confidence": item.confidence,
        "decision": item.decision,
        "evidence": list(item.evidence),
        "gpu_required": item.gpu_required,
        "output_bytes": _range(item.output_bytes),
        "peak_bytes": _range(item.peak_bytes),
        "stage": item.stage,
        "time": _time(item.time),
        "work": _work(item.work),
    }


def _device(item: DeviceBudget) -> dict[str, Any]:
    rotational: bool | None = item.rotational
    return {
        "accessible": item.accessible,
        "actions": list(item.actions),
        "decision": item.decision,
        "device_id": item.device_id,
        "filesystem": item.filesystem,
        "free_bytes": item.free_bytes,
        "path": item.path,
        "peak": _range(item.peak),
        "reserve_bytes": item.reserve_bytes,
        "roots": list(item.roots),
        "rotational": rotational,
        "storage_classes": list(item.storage_classes),
    }


def _host(host: HostAssumptions) -> dict[str, Any]:
    return {
        "device_id": host.device_id,
        "gpu_name": host.gpu_name,
        "gpu_total_gib": host.gpu_total_gib,
        "ram_available_gib": host.ram_available_gib,
        "workers": host.workers,
    }


def _coefficient(item: Coefficient) -> dict[str, Any]:
    return {
        "evidence_id": item.evidence_id,
        "name": item.name,
        "source": item.source,
        "value": item.value,
    }

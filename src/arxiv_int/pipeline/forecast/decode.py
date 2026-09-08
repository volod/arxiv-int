"""Reconstruct a ForecastDocument from a stored JSON object."""

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


def document_from_payload(payload: dict[str, Any]) -> ForecastDocument:
    """Parse a decision.json object."""
    outputs = payload["outputs"]
    return ForecastDocument(
        schema=str(payload.get("schema", SCHEMA_ID)),
        forecast_id=str(payload["forecast_id"]),
        run_id=None if payload.get("run_id") is None else str(payload["run_id"]),
        production=bool(payload["production"]),
        profile=str(payload["profile"]),
        plan=tuple(str(name) for name in payload["plan"]),
        not_selected=tuple(str(name) for name in payload.get("not_selected", ())),
        decision=str(payload["decision"]),
        confidence=str(payload["confidence"]),
        fingerprint=str(payload["fingerprint"]),
        config_fingerprint=str(payload["config_fingerprint"]),
        source_snapshot=str(payload["source_snapshot"]),
        envelope_fingerprint=str(payload["envelope_fingerprint"]),
        inventory_source=str(payload["inventory_source"]),
        stages=tuple(_stage(item) for item in payload["stages"]),
        devices=tuple(_device(item) for item in payload["devices"]),
        outputs=_outputs(outputs),
        time=_time(payload["time"]),
        critical_path=tuple(str(name) for name in payload["critical_path"]),
        host=_host(payload["host"]),
        coefficients=tuple(_coefficient(item) for item in payload["coefficients"]),
        actions=tuple(str(item) for item in payload["actions"]),
        excluded=tuple(str(item) for item in payload.get("excluded", ())),
    )


def _range(payload: dict[str, Any]) -> ByteRange:
    return ByteRange(int(payload["lower"]), int(payload["upper"]))


def _time(payload: dict[str, Any]) -> TimeRange:
    return TimeRange(float(payload["lower_seconds"]), float(payload["upper_seconds"]))


def _work(payload: dict[str, Any]) -> WorkCounts:
    return WorkCounts(
        int(payload["input_files"]),
        int(payload["input_bytes"]),
        int(payload["added"]),
        int(payload["changed"]),
        int(payload["renamed"]),
        int(payload["removed"]),
        int(payload["cached"]),
        int(payload["recomputed"]),
    )


def _outputs(payload: dict[str, Any]) -> OutputCosts:
    return OutputCosts(
        normalized=_range(payload["normalized"]),
        database_heap=_range(payload["database_heap"]),
        indexes=_range(payload["indexes"]),
        vectors=_range(payload["vectors"]),
        graph=_range(payload["graph"]),
        artifacts=_range(payload["artifacts"]),
        logs=_range(payload["logs"]),
        backups=_range(payload["backups"]),
        wal=_range(payload["wal"]),
        temp=_range(payload["temp"]),
        staging=_range(payload["staging"]),
        rebuild=_range(payload["rebuild"]),
        rollback=_range(payload["rollback"]),
    )


def _stage(payload: dict[str, Any]) -> StageForecast:
    return StageForecast(
        str(payload["stage"]),
        _work(payload["work"]),
        _range(payload["output_bytes"]),
        _time(payload["time"]),
        _range(payload["peak_bytes"]),
        str(payload["decision"]),
        str(payload["confidence"]),
        bool(payload["cache_hit"]),
        bool(payload["gpu_required"]),
        tuple(str(item) for item in payload.get("actions", ())),
        tuple(str(item) for item in payload.get("evidence", ())),
    )


def _device(payload: dict[str, Any]) -> DeviceBudget:
    rotational = payload.get("rotational")
    return DeviceBudget(
        str(payload["device_id"]),
        tuple(str(item) for item in payload["roots"]),
        str(payload.get("path", "")),
        str(payload["filesystem"]),
        tuple(str(item) for item in payload["storage_classes"]),
        None if rotational is None else bool(rotational),
        int(payload["free_bytes"]),
        bool(payload["accessible"]),
        _range(payload["peak"]),
        int(payload["reserve_bytes"]),
        str(payload["decision"]),
        tuple(str(item) for item in payload.get("actions", ())),
    )


def _host(payload: dict[str, Any]) -> HostAssumptions:
    return HostAssumptions(
        float(payload["ram_available_gib"]),
        str(payload["gpu_name"]),
        float(payload["gpu_total_gib"]),
        str(payload["device_id"]),
        int(payload["workers"]),
    )


def _coefficient(payload: dict[str, Any]) -> Coefficient:
    return Coefficient(
        str(payload["name"]),
        float(payload["value"]),
        str(payload["source"]),
        str(payload["evidence_id"]),
    )

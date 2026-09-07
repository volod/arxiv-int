"""Pure estimator: captured evidence in, fingerprinted decision out."""

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.forecast.codec import document_payload
from arxiv_int.pipeline.forecast.devices import budget_devices
from arxiv_int.pipeline.forecast.estimate import (
    envelope_coefficients,
    estimate_outputs,
    estimate_time,
    peak_total,
    work_counts,
)
from arxiv_int.pipeline.forecast.inputs import ForecastInputs
from arxiv_int.pipeline.forecast.model import (
    SCHEMA_ID,
    ByteRange,
    DeviceBudget,
    ForecastDocument,
    StageForecast,
    TimeRange,
)

EXCLUDED = ("archive-organization",)


def build_forecast(inputs: ForecastInputs) -> ForecastDocument:
    """Replayable decision from inventory, cache, telemetry, and device evidence."""
    outputs = estimate_outputs(inputs)
    rotational = _rotational_outputs(inputs)
    uncached = tuple(name for name in inputs.plan if not inputs.cache.hit(name))
    share = max(len(uncached), 1)
    persistent = peak_total(outputs)
    stages = tuple(
        _stage_forecast(name, inputs, persistent, share, rotational) for name in inputs.plan
    )
    devices = budget_devices(inputs.devices, outputs, inputs.envelope)
    time = _sum_time(stages)
    decision, confidence, actions = _overall(stages, devices, inputs)
    return ForecastDocument(
        schema=SCHEMA_ID,
        forecast_id=inputs.forecast_id,
        run_id=inputs.run_id,
        production=inputs.production,
        profile=inputs.profile,
        plan=inputs.plan,
        not_selected=inputs.not_selected,
        decision=decision,
        confidence=confidence,
        fingerprint=fingerprint_inputs(inputs),
        config_fingerprint=inputs.config_fingerprint,
        source_snapshot=inputs.source_snapshot,
        envelope_fingerprint=inputs.envelope_fingerprint,
        inventory_source=inputs.inventory.source,
        stages=stages,
        devices=devices,
        outputs=outputs,
        time=time,
        critical_path=inputs.plan,
        host=inputs.host,
        coefficients=envelope_coefficients(inputs),
        actions=actions,
        excluded=EXCLUDED,
    )


def fingerprint_inputs(inputs: ForecastInputs) -> str:
    """Hash estimate inputs, excluding live free-space samples."""
    payload = {
        "cache": [[name, int(hit), size] for name, hit, size in inputs.cache.hits],
        "config_fingerprint": inputs.config_fingerprint,
        "envelope_fingerprint": inputs.envelope_fingerprint,
        "inventory": inputs.inventory.fingerprint,
        "plan": list(inputs.plan),
        "profile": inputs.profile,
        "source_snapshot": inputs.source_snapshot,
    }
    return sha256_text(normalize_json(payload))


def fingerprint_document(document: ForecastDocument) -> str:
    """Hash a serialized document after clearing the fingerprint field."""
    payload = document_payload(document)
    payload["fingerprint"] = ""
    return sha256_text(normalize_json(payload))


def _stage_forecast(
    name: str,
    inputs: ForecastInputs,
    persistent: ByteRange,
    share: int,
    rotational: bool,
) -> StageForecast:
    work = work_counts(inputs, name)
    cached = inputs.cache.hit(name)
    declared = inputs.estimates.get(name)
    gpu = name in inputs.gpu_stages or (declared is not None and declared.gpu_required)
    if cached:
        output = ByteRange(0, inputs.envelope.log_bytes_per_stage)
        peak = output
    else:
        output = ByteRange(persistent.lower // share, persistent.upper // share)
        peak = output
    time = estimate_time(inputs, name, rotational=rotational)
    decision, confidence, actions, evidence = _stage_decision(name, inputs, gpu, cached)
    return StageForecast(
        stage=name,
        work=work,
        output_bytes=output,
        time=time,
        peak_bytes=peak,
        decision=decision,
        confidence=confidence,
        cache_hit=cached,
        gpu_required=gpu,
        actions=actions,
        evidence=evidence,
    )


def _stage_decision(
    name: str,
    inputs: ForecastInputs,
    gpu: bool,
    cached: bool,
) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
    evidence = [inputs.inventory.source, inputs.inventory.fingerprint[:12]]
    if inputs.comparable:
        evidence.append(f"telemetry:{inputs.comparable[0].run_id}")
    if cached:
        return "ready", "high", (), tuple(evidence)
    if gpu and inputs.host.gpu_name == "none":
        return "degraded", "low", (f"stage {name} requires a GPU",), tuple(evidence)
    large = inputs.inventory.bytes >= inputs.envelope.large_input_bytes
    if large and not inputs.comparable:
        return (
            "unknown",
            "low",
            ("run a bounded 0.1-1% or 50-200 GB pilot before this large stage",),
            tuple(evidence),
        )
    if inputs.inventory.source == "sample" or inputs.inventory.truncated or not inputs.comparable:
        return (
            "degraded",
            "low",
            ("conservative envelope; measured amplification is absent",),
            tuple(evidence),
        )
    return "ready", "medium", (), tuple(evidence)


def _overall(
    stages: tuple[StageForecast, ...],
    devices: tuple[DeviceBudget, ...],
    inputs: ForecastInputs,
) -> tuple[str, str, tuple[str, ...]]:
    blocked = _first_blocked(devices, stages)
    if blocked is not None:
        return blocked
    confidence = _confidence(stages, inputs)
    if _is_degraded(stages, devices, confidence):
        return (
            "degraded",
            confidence,
            ("proceed with conservative ranges and recheck free space at stage boundaries",),
        )
    return "ready", confidence, ()


def _first_blocked(
    devices: tuple[DeviceBudget, ...],
    stages: tuple[StageForecast, ...],
) -> tuple[str, str, tuple[str, ...]] | None:
    if any(item.decision == "blocked" for item in devices):
        return "blocked", "low", _flatten_actions(devices)
    if any(item.decision == "blocked" for item in stages):
        return "blocked", "low", _flatten_actions(stages)
    if any(item.decision == "unknown" for item in stages):
        return (
            "blocked",
            "low",
            _flatten_actions(stages) or ("unknown large-stage estimate requires a bounded pilot",),
        )
    return None


def _flatten_actions(
    items: tuple[StageForecast, ...] | tuple[DeviceBudget, ...],
) -> tuple[str, ...]:
    return tuple(dict.fromkeys(action for item in items for action in item.actions))


def _confidence(stages: tuple[StageForecast, ...], inputs: ForecastInputs) -> str:
    if inputs.comparable and inputs.inventory.source != "sample" and not inputs.inventory.truncated:
        if all(item.cache_hit or item.confidence != "low" for item in stages):
            return "high"
        return "medium"
    return "low"


def _is_degraded(
    stages: tuple[StageForecast, ...],
    devices: tuple[DeviceBudget, ...],
    confidence: str,
) -> bool:
    return (
        any(item.decision == "degraded" for item in stages)
        or any(item.decision == "degraded" for item in devices)
        or confidence == "low"
    )


def _rotational_outputs(inputs: ForecastInputs) -> bool:
    return any(
        item.rotational is True and item.storage_class in {"database", "scratch", "bulk"}
        for item in inputs.devices
    )


def _sum_time(stages: tuple[StageForecast, ...]) -> TimeRange:
    return TimeRange(
        sum(item.time.lower_seconds for item in stages),
        sum(item.time.upper_seconds for item in stages),
    )

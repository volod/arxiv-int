"""Conservative time and storage ranges from captured evidence."""

from arxiv_int.pipeline.forecast.inputs import ForecastInputs
from arxiv_int.pipeline.forecast.model import (
    ByteRange,
    Coefficient,
    OutputCosts,
    TimeRange,
    WorkCounts,
)

GIB = 1024**3
_PERSISTENT = (
    "normalized",
    "database_heap",
    "indexes",
    "vectors",
    "graph",
    "artifacts",
    "logs",
    "backups",
)


def work_counts(inputs: ForecastInputs, stage: str) -> WorkCounts:
    """Derive added/changed/cached/recomputed counts for one stage."""
    inventory = inputs.inventory
    cached = inputs.cache.hit(stage)
    recomputed = 0 if cached else max(inventory.added + inventory.changed + inventory.renamed, 1)
    return WorkCounts(
        input_files=inventory.files,
        input_bytes=inventory.bytes,
        added=inventory.added,
        changed=inventory.changed,
        renamed=inventory.renamed,
        removed=inventory.removed,
        cached=1 if cached else 0,
        recomputed=0 if cached else recomputed,
    )


def estimate_outputs(inputs: ForecastInputs) -> OutputCosts:
    """Apply the 2.5-4.0 envelope, then split into output and peak families."""
    envelope = inputs.envelope
    indexed = max(inputs.inventory.bytes, 1)
    factor = envelope.truncated_upper_factor if inputs.inventory.truncated else 1.0
    lower = int(indexed * envelope.amplification_lower)
    upper = int(indexed * envelope.amplification_upper * factor)
    weights = _active_families(inputs)
    persistent = {name: _share(lower, upper, weights.get(name, 0.0)) for name in _PERSISTENT}
    wal = _share(
        persistent["database_heap"].lower, persistent["database_heap"].upper, envelope.wal_fraction
    )
    temp = _share(lower, upper, envelope.temp_fraction)
    staging = _share(lower, upper, envelope.staging_fraction)
    rebuild_base = _add(
        persistent["indexes"],
        _add(persistent["vectors"], persistent["graph"]),
    )
    rebuild = ByteRange(
        int(rebuild_base.lower * envelope.rebuild_multiplier),
        int(rebuild_base.upper * envelope.rebuild_multiplier),
    )
    rollback = _share(staging.lower, staging.upper, envelope.rollback_fraction)
    backups = persistent["backups"]
    if envelope.backup_fraction <= 0:
        backups = ByteRange(0, 0)
    return OutputCosts(
        normalized=persistent["normalized"],
        database_heap=persistent["database_heap"],
        indexes=persistent["indexes"],
        vectors=persistent["vectors"],
        graph=persistent["graph"],
        artifacts=persistent["artifacts"],
        logs=persistent["logs"],
        backups=backups,
        wal=wal,
        temp=temp,
        staging=staging,
        rebuild=rebuild,
        rollback=rollback,
    )


def estimate_time(inputs: ForecastInputs, stage: str, *, rotational: bool) -> TimeRange:
    """Bound wall-clock time from comparable telemetry or declared seconds/GiB."""
    if inputs.cache.hit(stage):
        return TimeRange(0.0, 1.0)
    gib = max(inputs.inventory.bytes / GIB, 1.0 / 1024)
    lower, upper, _source = _telemetry_or_envelope(inputs, stage, gib)
    if rotational:
        lower *= inputs.envelope.rotational_time_lower
        upper *= inputs.envelope.rotational_time_upper
    declared = inputs.estimates.get(stage)
    if declared is not None:
        lower = max(lower, declared.cpu_seconds)
        upper = max(upper, declared.cpu_seconds * 4.0)
    return TimeRange(lower, max(lower, upper))


def envelope_coefficients(inputs: ForecastInputs) -> tuple[Coefficient, ...]:
    """List every bound the decision used, with provenance."""
    envelope = inputs.envelope
    source = "telemetry" if inputs.comparable else "envelope"
    evidence = inputs.comparable[0].run_id if inputs.comparable else "declared-envelope"
    items = [
        Coefficient("amplification_lower", envelope.amplification_lower, "envelope", evidence),
        Coefficient("amplification_upper", envelope.amplification_upper, "envelope", evidence),
        Coefficient(
            "safety_reserve_bytes", float(envelope.safety_reserve_bytes), "envelope", evidence
        ),
        Coefficient("wal_fraction", envelope.wal_fraction, "envelope", evidence),
        Coefficient("temp_fraction", envelope.temp_fraction, "envelope", evidence),
        Coefficient("staging_fraction", envelope.staging_fraction, "envelope", evidence),
        Coefficient("rebuild_multiplier", envelope.rebuild_multiplier, "envelope", evidence),
        Coefficient("seconds_per_gib_lower", envelope.seconds_per_gib_lower, source, evidence),
        Coefficient("seconds_per_gib_upper", envelope.seconds_per_gib_upper, source, evidence),
    ]
    if inputs.inventory.truncated:
        items.append(
            Coefficient(
                "truncated_upper_factor",
                envelope.truncated_upper_factor,
                "sample",
                inputs.inventory.fingerprint,
            )
        )
    return tuple(items)


def peak_total(outputs: OutputCosts) -> ByteRange:
    """Sum peak families without assigning them to devices."""
    return _sum_ranges(
        (
            outputs.normalized,
            outputs.database_heap,
            outputs.indexes,
            outputs.vectors,
            outputs.graph,
            outputs.artifacts,
            outputs.logs,
            outputs.backups,
            outputs.wal,
            outputs.temp,
            outputs.staging,
            outputs.rebuild,
            outputs.rollback,
        )
    )


def _active_families(inputs: ForecastInputs) -> dict[str, float]:
    plan = set(inputs.plan)
    weights = dict(inputs.envelope.families)
    if "load-vector" not in plan and "embed" not in plan:
        weights["vectors"] = 0.0
    if "graph" not in plan:
        weights["graph"] = 0.0
    if "load-lexical" not in plan:
        weights["indexes"] = min(weights.get("indexes", 0.0), 0.05)
    return weights


def _telemetry_or_envelope(
    inputs: ForecastInputs, stage: str, gib: float
) -> tuple[float, float, str]:
    matched = [
        run.stage_seconds[stage] * (inputs.inventory.bytes / max(run.input_bytes, 1))
        for run in inputs.comparable
        if stage in run.stage_seconds and run.stage_seconds[stage] > 0
    ]
    if matched:
        return min(matched), max(matched), "telemetry"
    envelope = inputs.envelope
    return envelope.seconds_per_gib_lower * gib, envelope.seconds_per_gib_upper * gib, "envelope"


def _share(lower: int, upper: int, fraction: float) -> ByteRange:
    if fraction <= 0:
        return ByteRange(0, 0)
    return ByteRange(int(lower * fraction), int(upper * fraction))


def _add(left: ByteRange, right: ByteRange) -> ByteRange:
    return ByteRange(left.lower + right.lower, left.upper + right.upper)


def _sum_ranges(ranges: tuple[ByteRange, ...]) -> ByteRange:
    total = ByteRange(0, 0)
    for item in ranges:
        total = _add(total, item)
    return total

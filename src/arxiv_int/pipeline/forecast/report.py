"""Secret-free console rendering for a forecast decision."""

from arxiv_int.pipeline.forecast.model import ForecastDocument


def console_lines(document: ForecastDocument) -> tuple[str, ...]:
    """Render one ASCII line group for logs and Make output."""
    lines = [
        f"forecast_id={document.forecast_id}",
        f"run_id={document.run_id or 'none'}",
        f"production={str(document.production).lower()}",
        f"decision={document.decision}",
        f"confidence={document.confidence}",
        f"fingerprint={document.fingerprint}",
        (
            f"time_s={document.time.lower_seconds:.1f}-{document.time.upper_seconds:.1f} "
            f"inventory={document.inventory_source}"
        ),
    ]
    for stage in document.stages:
        lines.append(
            f"stage {stage.stage}: cache_hit={str(stage.cache_hit).lower()} "
            f"added={stage.work.added} changed={stage.work.changed} "
            f"recomputed={stage.work.recomputed} "
            f"output_bytes={stage.output_bytes.lower}-{stage.output_bytes.upper} "
            f"time_s={stage.time.lower_seconds:.1f}-{stage.time.upper_seconds:.1f} "
            f"decision={stage.decision}"
        )
    for device in document.devices:
        rotational = "unknown" if device.rotational is None else str(device.rotational).lower()
        lines.append(
            f"device {device.device_id}: roots={','.join(device.roots)} "
            f"free_bytes={device.free_bytes} peak={device.peak.lower}-{device.peak.upper} "
            f"reserve={device.reserve_bytes} rotational={rotational} decision={device.decision}"
        )
    for action in document.actions:
        lines.append(f"action: {action}")
    if document.excluded:
        lines.append("excluded=" + ",".join(document.excluded))
    return tuple(lines)

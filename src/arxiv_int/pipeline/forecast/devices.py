"""Inspect configured roots, deduplicate devices, and budget peak plus reserve."""

from collections.abc import Callable, Mapping
from pathlib import Path

from arxiv_int.pipeline.forecast.estimate import peak_total
from arxiv_int.pipeline.forecast.inputs import DeviceSnapshot, Envelope
from arxiv_int.pipeline.forecast.model import (
    ByteRange,
    DeviceBudget,
    OutputCosts,
)
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.filesystem import FilesystemEvidence, inspect_filesystem
from arxiv_int.runtime.path_model import RootPlacement, runtime_placements

Inspector = Callable[[Path], FilesystemEvidence]

_CATEGORY_ROOT: Mapping[str, str] = {
    "artifacts": "RESULTS_DIR",
    "backups": "",
    "database_heap": "PGDATA_DIR",
    "graph": "PGDATA_DIR",
    "indexes": "PGDATA_DIR",
    "logs": "RUNS_DIR",
    "normalized": "RESULTS_DIR",
    "rebuild": "PGDATA_DIR",
    "rollback": "RUNS_DIR",
    "staging": "RUNS_DIR",
    "temp": "TMP_DIR",
    "vectors": "PGDATA_DIR",
    "wal": "PG_WAL_DIR",
}


def collect_devices(
    config: RuntimeConfig,
    inspector: Inspector | None = None,
) -> tuple[DeviceSnapshot, ...]:
    """Inspect every configured root, including uncreated output paths."""
    probe = inspector or inspect_filesystem
    snapshots: list[DeviceSnapshot] = []
    for placement in runtime_placements(config):
        snapshots.append(_snapshot(placement, probe))
    return tuple(snapshots)


def budget_devices(
    snapshots: tuple[DeviceSnapshot, ...],
    outputs: OutputCosts,
    envelope: Envelope,
) -> tuple[DeviceBudget, ...]:
    """Charge each cost family to one root, then sum per device id."""
    by_variable = {item.variable: item for item in snapshots}
    grouped: dict[str, list[DeviceSnapshot]] = {}
    for item in snapshots:
        grouped.setdefault(item.device_id, []).append(item)
    budgets: list[DeviceBudget] = []
    for device_id, members in sorted(grouped.items()):
        peak = _device_peak(members, by_variable, outputs)
        reserve = _reserve(envelope, peak.upper)
        accessible = all(item.accessible for item in members)
        rotational = (
            True
            if any(item.rotational is True for item in members)
            else (False if all(item.rotational is False for item in members) else None)
        )
        decision, actions = _device_decision(accessible, members, peak, reserve)
        budgets.append(
            DeviceBudget(
                device_id=device_id,
                roots=tuple(item.variable for item in members),
                path=members[0].path,
                filesystem=members[0].filesystem,
                storage_classes=tuple(sorted({item.storage_class for item in members})),
                rotational=rotational,
                free_bytes=members[0].free_bytes if accessible else 0,
                accessible=accessible,
                peak=peak,
                reserve_bytes=reserve,
                decision=decision,
                actions=actions,
            )
        )
    return tuple(budgets)


def required_headroom(envelope: Envelope, peak_upper: int) -> int:
    """Hard reserve plus a fraction of the upper-bound peak."""
    return _reserve(envelope, peak_upper)


def combined_peak(outputs: OutputCosts) -> ByteRange:
    """Total peak before device assignment; used by tests."""
    return peak_total(outputs)


def _snapshot(placement: RootPlacement, inspector: Inspector) -> DeviceSnapshot:
    try:
        evidence = inspector(placement.path)
    except OSError:
        return DeviceSnapshot(
            placement.variable,
            str(placement.path),
            "inaccessible",
            "unknown",
            placement.storage_class,
            None,
            0,
            False,
            True,
        )
    return DeviceSnapshot(
        placement.variable,
        str(evidence.path),
        evidence.device_id,
        evidence.filesystem,
        placement.storage_class,
        evidence.rotational,
        evidence.free_bytes,
        True,
        evidence.read_only,
    )


def _device_peak(
    members: list[DeviceSnapshot],
    by_variable: Mapping[str, DeviceSnapshot],
    outputs: OutputCosts,
) -> ByteRange:
    variables = {item.variable for item in members}
    total = ByteRange(0, 0)
    for category, variable in _CATEGORY_ROOT.items():
        assigned = _assigned_root(variable, by_variable)
        if assigned is None or assigned not in variables:
            continue
        span = getattr(outputs, category)
        total = ByteRange(total.lower + span.lower, total.upper + span.upper)
    return total


def _assigned_root(variable: str, by_variable: Mapping[str, DeviceSnapshot]) -> str | None:
    if not variable:
        return None
    if variable in by_variable:
        return variable
    if variable == "PG_WAL_DIR":
        return "PGDATA_DIR" if "PGDATA_DIR" in by_variable else None
    return None


def _reserve(envelope: Envelope, peak_upper: int) -> int:
    return max(envelope.safety_reserve_bytes, int(peak_upper * envelope.safety_reserve_ratio))


def _device_decision(
    accessible: bool,
    members: list[DeviceSnapshot],
    peak: ByteRange,
    reserve: int,
) -> tuple[str, tuple[str, ...]]:
    source_only = all(item.storage_class == "source" for item in members)
    if not accessible:
        names = ",".join(item.variable for item in members)
        return "blocked", (f"inaccessible path for {names}",)
    if source_only:
        return "ready", ()
    needed = peak.upper + reserve
    free = members[0].free_bytes
    if free < needed:
        return "blocked", (
            f"upper-bound peak {peak.upper} plus reserve {reserve} exceeds free {free}",
        )
    if any(
        item.rotational is True and item.storage_class in {"database", "scratch"}
        for item in members
    ):
        return "degraded", ("rotational database or scratch device widens time range",)
    return "ready", ()

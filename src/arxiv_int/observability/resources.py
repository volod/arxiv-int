"""CPU, RAM, disk, NVML/nvidia-smi, and optional Postgres size samples."""

import shutil
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from arxiv_int.inference.resources import read_gpus, read_ram, snapshot_host
from arxiv_int.observability.events import ResourceSample

_PROC_STAT = Path("/proc/stat")
_PROC_MEMINFO = Path("/proc/meminfo")
CommandRunner = Callable[[tuple[str, ...]], str]
PostgresSizer = Callable[[], tuple[int, int]]


class ResourceProbe(Protocol):
    """One host/store sample used by progress emission."""

    def sample(self) -> ResourceSample:
        """Return the current bounded resource snapshot."""


def _load_1m(path: Path = Path("/proc/loadavg")) -> float:
    if not path.is_file():
        return 0.0
    token = path.read_text(encoding="utf-8").split()[0]
    try:
        return float(token)
    except ValueError:
        return 0.0


def _cpu_pct_psutil() -> float | None:
    try:
        import psutil  # type: ignore[import-untyped]
    except ImportError:
        return None
    return float(psutil.cpu_percent(interval=None))


def _cpu_pct_from_stat(
    path: Path, previous: tuple[int, int] | None
) -> tuple[float, tuple[int, int]]:
    if not path.is_file():
        return 0.0, previous or (0, 0)
    first = path.read_text(encoding="utf-8").splitlines()[0]
    parts = first.split()
    if len(parts) < 5 or parts[0] != "cpu":
        return 0.0, previous or (0, 0)
    values = [int(item) for item in parts[1:8]]
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    total = sum(values)
    if previous is None or total <= previous[1]:
        return 0.0, (idle, total)
    idle_delta = idle - previous[0]
    total_delta = total - previous[1]
    if total_delta <= 0:
        return 0.0, (idle, total)
    busy = max(0.0, 1.0 - (idle_delta / total_delta))
    return busy * 100.0, (idle, total)


class FixedResourceSampler:
    """Return one prebuilt sample; used by tests and hosts without probes."""

    def __init__(self, sample: ResourceSample | None = None) -> None:
        self._sample = sample or ResourceSample()

    def sample(self) -> ResourceSample:
        return self._sample


class ResourceSampler:
    """Collect bounded host metrics; collectors are injectable for tests."""

    def __init__(
        self,
        *,
        disk_root: Path,
        meminfo: Path | None = None,
        gpu_runner: CommandRunner | None = None,
        postgres_sizer: PostgresSizer | None = None,
        stat_path: Path | None = None,
        loadavg_path: Path | None = None,
    ) -> None:
        self._disk_root = disk_root
        self._meminfo = meminfo if meminfo is not None else _PROC_MEMINFO
        self._gpu_runner = gpu_runner
        self._postgres_sizer = postgres_sizer
        self._stat_path = stat_path if stat_path is not None else _PROC_STAT
        self._loadavg_path = loadavg_path if loadavg_path is not None else Path("/proc/loadavg")
        self._cpu_prev: tuple[int, int] | None = None

    def sample(self) -> ResourceSample:
        """Return one CPU/RAM/disk/GPU/Postgres snapshot."""
        ram = read_ram(self._meminfo)
        usage = shutil.disk_usage(self._disk_root)
        cpu = _cpu_pct_psutil()
        if cpu is None:
            had_prev = self._cpu_prev is not None
            cpu, self._cpu_prev = _cpu_pct_from_stat(self._stat_path, self._cpu_prev)
            if not had_prev:
                cpu = min(100.0, _load_1m(self._loadavg_path) * 10.0)
        host = snapshot_host(runner=self._gpu_runner, meminfo=self._meminfo)
        pg_size, wal = (0, 0) if self._postgres_sizer is None else self._postgres_sizer()
        return ResourceSample(
            cpu_pct=round(cpu, 2),
            ram_available_gib=ram.available_gib,
            ram_total_gib=ram.total_gib,
            disk_free_gib=usage.free / (1024**3),
            disk_total_gib=usage.total / (1024**3),
            gpu_util_pct=host.gpu_util_pct,
            gpu_free_gib=host.free_gpu_gib,
            gpu_used_gib=host.used_gpu_gib,
            gpu_total_gib=host.total_gpu_gib,
            gpu_power_watts=host.power_watts,
            pg_size_bytes=pg_size,
            wal_bytes=wal,
            device=host.device_id,
        )


def postgres_size_query(execute: Callable[[str], tuple[int, int] | None]) -> PostgresSizer:
    """Wrap a SQL executor that returns (database_bytes, wal_bytes)."""

    def sample() -> tuple[int, int]:
        try:
            result = execute(
                "SELECT pg_database_size(current_database()), "
                "COALESCE((SELECT sum(size) FROM pg_ls_waldir()), 0)"
            )
        except Exception:
            return (0, 0)
        if result is None:
            return (0, 0)
        return result

    return sample


__all__ = [
    "FixedResourceSampler",
    "ResourceProbe",
    "ResourceSampler",
    "postgres_size_query",
    "read_gpus",
    "read_ram",
]

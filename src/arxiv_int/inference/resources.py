"""Host GPU and RAM snapshots used by model-fit decisions."""

import subprocess
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.inference.footprint import DEFAULT_DB_RESERVE_GIB

_NVIDIA_QUERY = (
    "nvidia-smi",
    "--query-gpu=index,name,memory.total,memory.free,memory.used,utilization.gpu,power.draw",
    "--format=csv,noheader,nounits",
)
_MEMINFO = Path("/proc/meminfo")


@dataclass(frozen=True, slots=True)
class GpuDevice:
    """One NVIDIA device as reported by nvidia-smi."""

    index: int
    name: str
    total_gib: float
    free_gib: float
    used_gib: float
    utilization_pct: float
    power_watts: float

    @property
    def device_id(self) -> str:
        return f"cuda:{self.index}"


@dataclass(frozen=True, slots=True)
class RamSnapshot:
    """Host RAM in GiB."""

    total_gib: float
    available_gib: float


@dataclass(frozen=True, slots=True)
class HostSnapshot:
    """One-host resource observation for placement and telemetry."""

    ram: RamSnapshot
    gpus: tuple[GpuDevice, ...]
    database_reserve_gib: float = DEFAULT_DB_RESERVE_GIB

    @property
    def free_gpu_gib(self) -> float:
        return self.gpus[0].free_gib if self.gpus else 0.0

    @property
    def used_gpu_gib(self) -> float:
        return self.gpus[0].used_gib if self.gpus else 0.0

    @property
    def total_gpu_gib(self) -> float:
        return self.gpus[0].total_gib if self.gpus else 0.0

    @property
    def power_watts(self) -> float:
        return self.gpus[0].power_watts if self.gpus else 0.0

    @property
    def gpu_util_pct(self) -> float:
        return self.gpus[0].utilization_pct if self.gpus else 0.0

    @property
    def gpu_name(self) -> str:
        return self.gpus[0].name if self.gpus else "none"

    @property
    def device_id(self) -> str:
        return self.gpus[0].device_id if self.gpus else "cpu"

    @property
    def available_ram_gib(self) -> float:
        return self.ram.available_gib


CommandRunner = Callable[[tuple[str, ...]], str]


def snapshot_host(
    *,
    runner: CommandRunner | None = None,
    meminfo: Path | None = None,
    database_reserve_gib: float = DEFAULT_DB_RESERVE_GIB,
) -> HostSnapshot:
    """Read RAM and NVIDIA VRAM without forecasting pipeline duration."""
    ram = read_ram(meminfo if meminfo is not None else _MEMINFO)
    gpus = read_gpus(runner if runner is not None else _run_nvidia_smi)
    return HostSnapshot(ram=ram, gpus=gpus, database_reserve_gib=database_reserve_gib)


def read_ram(meminfo: Path) -> RamSnapshot:
    """Parse MemTotal/MemAvailable from a meminfo file."""
    values = _meminfo_values(meminfo)
    total = values.get("MemTotal")
    available = values.get("MemAvailable", values.get("MemFree"))
    if total is None or available is None:
        return RamSnapshot(0.0, 0.0)
    return RamSnapshot(_kib_to_gib(total), _kib_to_gib(available))


def read_gpus(runner: CommandRunner) -> tuple[GpuDevice, ...]:
    """Parse nvidia-smi CSV, or return no devices when the utility is absent."""
    try:
        text = runner(_NVIDIA_QUERY)
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        return ()
    return parse_nvidia_smi_csv(text)


def parse_nvidia_smi_csv(text: str) -> tuple[GpuDevice, ...]:
    """Parse one nvidia-smi CSV body into GPU devices."""
    devices: list[GpuDevice] = []
    for line in text.splitlines():
        device = _parse_gpu_line(line)
        if device is not None:
            devices.append(device)
    return tuple(devices)


def _parse_gpu_line(line: str) -> GpuDevice | None:
    stripped = line.strip()
    if not stripped or stripped.lower().startswith("index"):
        return None
    parts = [item.strip() for item in stripped.split(",")]
    if len(parts) < 5:
        return None
    try:
        index = int(_numeric_token(parts[0]))
    except ValueError:
        return None
    util = _optional_float(parts[5]) if len(parts) > 5 else 0.0
    power = _optional_float(parts[6]) if len(parts) > 6 else 0.0
    return GpuDevice(
        index=index,
        name=parts[1],
        total_gib=_mib_to_gib(parts[2]),
        free_gib=_mib_to_gib(parts[3]),
        used_gib=_mib_to_gib(parts[4]),
        utilization_pct=util,
        power_watts=power,
    )


def _run_nvidia_smi(command: tuple[str, ...]) -> str:
    completed = subprocess.run(command, capture_output=True, text=True, check=True, timeout=5)
    return completed.stdout


def _meminfo_values(path: Path) -> Mapping[str, int]:
    if not path.is_file():
        return {}
    values: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        token = rest.strip().split()[0]
        try:
            values[name] = int(token)
        except ValueError:
            continue
    return values


def _kib_to_gib(kib: int) -> float:
    return kib / (1024 * 1024)


def _mib_to_gib(value: str) -> float:
    return _optional_float(value) / 1024.0


def _optional_float(value: str) -> float:
    token = _numeric_token(value)
    if not token or "n/a" in token.lower():
        return 0.0
    try:
        return float(token)
    except ValueError:
        return 0.0


def _numeric_token(value: str) -> str:
    return value.replace("MiB", "").replace("%", "").replace("W", "").strip()

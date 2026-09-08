"""Resource sampling uses injectable probes and live NVIDIA data when present."""

from pathlib import Path

import pytest

from arxiv_int.inference.resources import snapshot_host
from arxiv_int.observability.events import ResourceSample
from arxiv_int.observability.resources import ResourceSampler


def test_sampler_reads_injected_meminfo_disk_and_gpu(tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 1048576 kB\nMemAvailable: 524288 kB\n", encoding="utf-8")
    stat = tmp_path / "stat"
    stat.write_text("cpu  10 0 10 80 0 0 0\n", encoding="utf-8")
    disk = tmp_path / "disk"
    disk.mkdir()
    csv = "0, NVIDIA GeForce RTX 4060 Ti, 16380, 14709, 1671, 12, 40.0\n"
    sampler = ResourceSampler(
        disk_root=disk,
        meminfo=meminfo,
        gpu_runner=lambda _command: csv,
        postgres_sizer=lambda: (1024, 256),
        stat_path=stat,
        loadavg_path=tmp_path / "missing-loadavg",
    )
    first = sampler.sample()
    assert first.device == "cuda:0"
    assert first.gpu_free_gib > 14.0
    assert first.pg_size_bytes == 1024
    assert first.wal_bytes == 256
    stat.write_text("cpu  20 0 20 90 0 0 0\n", encoding="utf-8")
    second = sampler.sample()
    assert second.cpu_pct >= 0.0


def test_live_nvidia_snapshot_when_a_device_is_present() -> None:
    snapshot = snapshot_host()
    if not snapshot.gpus:
        pytest.skip("no NVIDIA device on this host")
    assert snapshot.gpus[0].total_gib > 0
    assert snapshot.device_id.startswith("cuda:")
    sample = ResourceSampler(disk_root=Path("/tmp")).sample()
    assert sample.device.startswith("cuda:")
    assert isinstance(sample, ResourceSample)

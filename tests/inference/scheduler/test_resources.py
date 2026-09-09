"""GPU/RAM snapshot parsing without calling a live driver."""

from pathlib import Path

from arxiv_int.inference.scheduler.resources import parse_nvidia_smi_csv, read_ram, snapshot_host

CSV = (
    "0, NVIDIA GeForce RTX 4060 Ti, 16380, 14953, 964, 33, 26.12\n"
    "1, other, 8192, [N/A], 0, [N/A], [N/A]\n"
)


def test_parses_nvidia_smi_csv_including_na_fields() -> None:
    devices = parse_nvidia_smi_csv(CSV)
    assert devices[0].name == "NVIDIA GeForce RTX 4060 Ti"
    assert devices[0].device_id == "cuda:0"
    assert 14.5 < devices[0].free_gib < 14.7
    assert devices[0].power_watts == 26.12
    assert devices[1].power_watts == 0.0
    assert devices[1].free_gib == 0.0


def test_reads_meminfo_and_accepts_injected_gpu_probe(tmp_path: Path) -> None:
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemTotal: 131651400 kB\nMemAvailable: 117252388 kB\n", encoding="utf-8")
    ram = read_ram(meminfo)
    assert 125.0 < ram.total_gib < 126.0
    assert 111.0 < ram.available_gib < 113.0
    snapshot = snapshot_host(runner=lambda _command: CSV, meminfo=meminfo, database_reserve_gib=4.0)
    assert snapshot.gpu_name.startswith("NVIDIA")
    assert snapshot.database_reserve_gib == 4.0
    assert snapshot.free_gpu_gib > 14.0

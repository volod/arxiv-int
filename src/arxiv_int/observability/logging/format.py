"""Human console lines for progress snapshots. ASCII only."""

from arxiv_int.observability.metrics.events import ProgressSnapshot


def format_progress(snapshot: ProgressSnapshot) -> str:
    """Render one operator console line for a progress snapshot."""
    eta = "unknown" if snapshot.eta_seconds is None else f"{snapshot.eta_seconds:.0f}s"
    resources = snapshot.resources
    return (
        f"{snapshot.ts} run={snapshot.run_id} stage={snapshot.stage} "
        f"shard={snapshot.shard_token} processed={snapshot.processed} "
        f"remaining={snapshot.remaining} bytes={snapshot.bytes} "
        f"rate={snapshot.throughput_per_s:.2f}/s eta={eta} "
        f"elapsed={snapshot.elapsed_seconds:.0f}s errors={snapshot.errors} "
        f"state={snapshot.worker_state} cpu={resources.cpu_pct:.0f}% "
        f"ram_free={resources.ram_available_gib:.1f}GiB "
        f"disk_free={resources.disk_free_gib:.1f}GiB "
        f"gpu={resources.gpu_util_pct:.0f}%/{resources.gpu_free_gib:.1f}GiB"
    )

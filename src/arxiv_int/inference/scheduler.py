"""Host-wide GPU coordination: fit, exclusive lease, lifecycle, and telemetry."""

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from time import monotonic

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.inference.errors import ModelFitError
from arxiv_int.inference.footprint import FootprintEstimate, ModelFootprint, estimate_footprint
from arxiv_int.inference.lease import HostGpuLease, ResourceLeaseRecord, lease_record
from arxiv_int.inference.lifecycle import (
    OccupancyProbe,
    VllmController,
    prepare_device,
    release_device,
)
from arxiv_int.inference.resources import HostSnapshot, snapshot_host
from arxiv_int.inference.scheduling import (
    ModelPlacement,
    ModelRequirement,
    OccupancySnapshot,
    place_requirement,
)
from arxiv_int.inference.telemetry import TelemetryEvent, TelemetrySink, telemetry_path

SnapshotFn = Callable[[], HostSnapshot]


@dataclass(frozen=True, slots=True)
class GrantedSession:
    """One exclusive GPU or explicit CPU session with the evidence that justified it."""

    placement: ModelPlacement
    estimate: FootprintEstimate
    snapshot: HostSnapshot
    occupancy: OccupancySnapshot
    lease: ResourceLeaseRecord | None
    actions: tuple[str, ...]


class ModelResourceScheduler:
    """Serialize GPU-heavy work on one host and record why a model ran or did not."""

    def __init__(
        self,
        *,
        lease: HostGpuLease,
        sink: TelemetrySink,
        run_id: str,
        client: LocalInferenceClient | None = None,
        vllm: VllmController | None = None,
        occupancy: OccupancyProbe | None = None,
        snapshot: SnapshotFn = snapshot_host,
        wait_seconds: float = 30.0,
    ) -> None:
        self._lease = lease
        self._sink = sink
        self._run_id = run_id
        self._client = client
        self._vllm = vllm
        self._occupancy = occupancy or OccupancyProbe(client=client, vllm=vllm)
        self._snapshot = snapshot
        self.wait_seconds = wait_seconds

    def decide(
        self,
        requirement: ModelRequirement,
        footprint: ModelFootprint,
        *,
        cancel: Event | None = None,
    ) -> tuple[HostSnapshot, OccupancySnapshot, FootprintEstimate, ModelPlacement]:
        snapshot = self._snapshot()
        occupancy = self._occupancy.probe(cancel)
        estimate = estimate_footprint(
            footprint, context_tokens=requirement.context_tokens, batch_size=requirement.batch_size
        )
        placement = place_requirement(requirement, snapshot, estimate, occupancy)
        self._emit("fit", requirement, snapshot, estimate, placement.device, placement.detail)
        return snapshot, occupancy, estimate, placement

    @contextmanager
    def session(
        self,
        requirement: ModelRequirement,
        footprint: ModelFootprint,
        *,
        cancel: Event | None = None,
    ) -> Iterator[GrantedSession]:
        snapshot, occupancy, estimate, placement = self.decide(
            requirement, footprint, cancel=cancel
        )
        if placement.device == "unavailable":
            self._reject(requirement, estimate, snapshot, placement.detail)
            raise ModelFitError(placement.detail)
        if placement.device == "cpu":
            self._emit("fallback", requirement, snapshot, estimate, "cpu", placement.detail)
            yield GrantedSession(placement, estimate, snapshot, occupancy, None, ())
            return
        row = _pending_row(self._run_id, requirement, estimate, snapshot, placement)
        with self._lease.hold(row, cancel=cancel, wait_seconds=self.wait_seconds) as held:
            start = monotonic()
            actions: tuple[str, ...] = ()
            try:
                actions = prepare_device(
                    requirement, occupancy, client=self._client, vllm=self._vllm, cancel=cancel
                )
                loaded = self._snapshot()
                self._emit(
                    "acquired",
                    requirement,
                    loaded,
                    estimate,
                    "cuda",
                    placement.detail,
                    lease_id=held.lease_id,
                    load_seconds=monotonic() - start,
                )
                yield GrantedSession(placement, estimate, loaded, occupancy, held, actions)
            finally:
                released = release_device(requirement, client=self._client, cancel=cancel)
                detail = "; ".join((*actions, *released)) or "lease released"
                self._emit(
                    "released",
                    requirement,
                    self._snapshot(),
                    estimate,
                    "cuda",
                    detail,
                    lease_id=held.lease_id,
                )

    def record_metrics(
        self,
        requirement: ModelRequirement,
        snapshot: HostSnapshot,
        estimate: FootprintEstimate,
        *,
        lease_id: str,
        throughput_tokens_per_s: float,
        load_seconds: float = 0.0,
        detail: str = "ok",
    ) -> None:
        self._emit(
            "metrics",
            requirement,
            snapshot,
            estimate,
            "cuda",
            detail,
            lease_id=lease_id,
            load_seconds=load_seconds,
            throughput=throughput_tokens_per_s,
        )

    def _reject(
        self,
        requirement: ModelRequirement,
        estimate: FootprintEstimate,
        snapshot: HostSnapshot,
        detail: str,
    ) -> None:
        self._lease.append_rejected(
            lease_record(
                run_id=self._run_id,
                model_id=requirement.model_id,
                backend=requirement.backend,
                workload=requirement.workload,
                device_id=snapshot.device_id,
                status="rejected",
                detail=detail,
                gpu_need_gib=estimate.gpu_gib,
                cpu_ram_gib=estimate.cpu_ram_gib,
            )
        )
        self._emit("rejected", requirement, snapshot, estimate, "unavailable", detail)

    def _emit(
        self,
        event: str,
        requirement: ModelRequirement,
        snapshot: HostSnapshot,
        estimate: FootprintEstimate,
        device: str,
        detail: str,
        *,
        lease_id: str = "",
        load_seconds: float = 0.0,
        throughput: float = 0.0,
    ) -> None:
        self._sink.record(
            TelemetryEvent(
                event=event,
                run_id=self._run_id,
                model_id=requirement.model_id,
                backend=requirement.backend,
                device=device,
                status=event,
                detail=detail,
                gpu_need_gib=estimate.gpu_gib,
                free_gpu_gib=snapshot.free_gpu_gib,
                used_gpu_gib=snapshot.used_gpu_gib,
                total_gpu_gib=snapshot.total_gpu_gib,
                ram_available_gib=snapshot.available_ram_gib,
                database_reserve_gib=snapshot.database_reserve_gib,
                power_watts=snapshot.power_watts,
                gpu_util_pct=snapshot.gpu_util_pct,
                load_seconds=load_seconds,
                throughput_tokens_per_s=throughput,
                lease_id=lease_id,
            )
        )


def _pending_row(
    run_id: str,
    requirement: ModelRequirement,
    estimate: FootprintEstimate,
    snapshot: HostSnapshot,
    placement: ModelPlacement,
) -> ResourceLeaseRecord:
    return lease_record(
        run_id=run_id,
        model_id=requirement.model_id,
        backend=requirement.backend,
        workload=requirement.workload,
        device_id=snapshot.device_id,
        status="acquired",
        detail=placement.detail,
        gpu_need_gib=estimate.gpu_gib,
        cpu_ram_gib=estimate.cpu_ram_gib,
    )


def scheduler_paths(
    service_state_dir: Path, runs_dir: Path, run_id: str
) -> tuple[HostGpuLease, TelemetrySink]:
    """Build the host lease ledger and run telemetry sink."""
    return HostGpuLease(service_state_dir / "inference"), TelemetrySink(
        telemetry_path(runs_dir, run_id)
    )

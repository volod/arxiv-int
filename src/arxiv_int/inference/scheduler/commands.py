"""Operator commands for GPU resource snapshot, model fit, and exclusive scheduling."""

import argparse
import logging
from threading import Event

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.inference.client.errors import LeaseCancelledError, LeaseConflictError, ModelFitError
from arxiv_int.inference.client.factory import (
    client_from_config,
    footprint_from_config,
    scheduler_from_config,
)
from arxiv_int.inference.policy.footprint import ModelFootprint
from arxiv_int.inference.scheduler import ModelResourceScheduler
from arxiv_int.inference.scheduler.resources import snapshot_host
from arxiv_int.inference.scheduler.scheduling import ModelRequirement
from arxiv_int.runtime.config_model import RuntimeConfig

_LOG = logging.getLogger(__name__)


def run_scheduler_command(
    args: argparse.Namespace, config: RuntimeConfig | None, cancel: Event | None
) -> int:
    """Dispatch resources, fit, and schedule subcommands."""
    if args.inference_command == "resources":
        return _run_resources()
    if config is None:
        raise ValueError("runtime configuration is required")
    client = client_from_config(config, timeout=args.timeout)
    try:
        if args.inference_command == "fit":
            return _run_fit(args, config, client)
        return _run_schedule(args, config, client, cancel)
    finally:
        client.close()


def _run_resources() -> int:
    snapshot = snapshot_host()
    if snapshot.gpus:
        gpu = snapshot.gpus[0]
        _LOG.info(
            "gpu=%s device=%s total_gib=%.1f free_gib=%.1f used_gib=%.1f util_pct=%.0f power_w=%.1f",
            gpu.name,
            gpu.device_id,
            gpu.total_gib,
            gpu.free_gib,
            gpu.used_gib,
            gpu.utilization_pct,
            gpu.power_watts,
        )
    else:
        _LOG.info("gpu=none")
    _LOG.info(
        "ram_total_gib=%.1f ram_available_gib=%.1f database_reserve_gib=%.1f",
        snapshot.ram.total_gib,
        snapshot.ram.available_gib,
        snapshot.database_reserve_gib,
    )
    return 0


def _run_fit(args: argparse.Namespace, config: RuntimeConfig, client: LocalInferenceClient) -> int:
    requirement, footprint, scheduler = _bind(args, config, client)
    placement = scheduler.decide(requirement, footprint)[3]
    _LOG.info(
        "placement=%s model=%s backend=%s %s",
        placement.device,
        requirement.model_id,
        requirement.backend,
        placement.detail,
    )
    return 0 if placement.device != "unavailable" else 2


def _run_schedule(
    args: argparse.Namespace,
    config: RuntimeConfig,
    client: LocalInferenceClient,
    cancel: Event | None,
) -> int:
    requirement, footprint, scheduler = _bind(args, config, client)
    try:
        with scheduler.session(requirement, footprint, cancel=cancel) as granted:
            lease_id = granted.lease.lease_id if granted.lease is not None else "-"
            _LOG.info(
                "scheduled placement=%s model=%s lease=%s actions=%s detail=%s",
                granted.placement.device,
                requirement.model_id,
                lease_id,
                ",".join(granted.actions) or "-",
                granted.placement.detail,
            )
    except ModelFitError as error:
        _LOG.error("%s", error)
        return 2
    except (LeaseCancelledError, LeaseConflictError) as error:
        _LOG.error("%s", error)
        return 1
    return 0


def _bind(
    args: argparse.Namespace, config: RuntimeConfig, client: LocalInferenceClient
) -> tuple[ModelRequirement, ModelFootprint, ModelResourceScheduler]:
    model_id = args.model or client.default_model
    if not model_id:
        raise ValueError("no generation model is configured")
    footprint = footprint_from_config(config, client.name, model_id)
    allow_cpu = footprint.allow_cpu if args.allow_cpu is None else args.allow_cpu
    requirement = ModelRequirement(
        model_id=model_id,
        allow_cpu=allow_cpu,
        backend=client.name,
        context_tokens=args.context,
        batch_size=args.batch,
        allow_service_control=bool(getattr(args, "allow_service_control", False)),
        workload=args.workload,
    )
    scheduler = scheduler_from_config(
        config, run_id=args.run_id, client=client, wait_seconds=args.wait_seconds
    )
    return requirement, footprint, scheduler

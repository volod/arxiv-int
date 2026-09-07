"""Bounded transport and model health wait that does not require a schema."""

from collections.abc import Callable
from time import monotonic

from arxiv_int.readiness.inference import check_inference
from arxiv_int.readiness.probes import Probe
from arxiv_int.readiness.report import PreflightReport
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.service_plan import ServicePlan, plan_services
from arxiv_int.runtime.setup.model import RETRY_COMMAND, PhaseResult
from arxiv_int.runtime.setup.state import fingerprint_for

Sleep = Callable[[float], None]
Cancelled = Callable[[], bool]
DEFAULT_WAIT_SECONDS = 120.0
POLL_INTERVAL = 2.0


def _probe_health(
    config: RuntimeConfig, plan: ServicePlan, probe: Probe, timeout: float
) -> PreflightReport:
    report = PreflightReport("setup-wait")
    check_inference(report, config, probe, timeout, vllm_service="vllm" in plan.services)
    return report


def _health_result(report: PreflightReport, plan: ServicePlan) -> PhaseResult | None:
    blocked = [item for item in report.findings if item.status == "blocked"]
    degraded = [item for item in report.findings if item.status == "degraded"]
    endpoint_ready = any(
        item.name == "inference.endpoint" and item.status == "ready" for item in report.findings
    )
    models_unready = any(
        item.name == "inference.models" and item.status != "ready" for item in report.findings
    )
    if endpoint_ready and models_unready:
        detail = (degraded or blocked)[0].detail if (degraded or blocked) else "models unavailable"
        return PhaseResult(
            "wait", "blocked", detail, action="make models-pull, then " + RETRY_COMMAND
        )
    if not blocked and not degraded:
        return PhaseResult(
            "wait",
            "ready",
            "service transport and model health passed",
            fingerprint=fingerprint_for(*plan.services),
        )
    return None


def run_wait_phase(
    config: RuntimeConfig,
    profiles: str,
    probe: Probe,
    *,
    timeout: float = 3.0,
    deadline_seconds: float = DEFAULT_WAIT_SECONDS,
    sleep: Sleep,
    cancelled: Cancelled,
    clock: Callable[[], float] = monotonic,
) -> PhaseResult:
    """Wait for selected service transport and model health, not catalog initialization."""
    plan = plan_services(profiles, project_root=config.project_root)
    deadline = clock() + deadline_seconds
    last_detail = "waiting for service and model health"
    while clock() < deadline:
        if cancelled():
            return PhaseResult("wait", "cancelled", "setup wait cancelled", action=RETRY_COMMAND)
        report = _probe_health(config, plan, probe, timeout)
        outcome = _health_result(report, plan)
        if outcome is not None:
            return outcome
        last_detail = next(
            (item.detail for item in report.findings if item.status != "ready"), last_detail
        )
        remaining = deadline - clock()
        if remaining <= 0:
            break
        sleep(min(POLL_INTERVAL, remaining))
    return PhaseResult(
        "wait",
        "blocked",
        f"timed out waiting for health: {last_detail}",
        action="inspect make services-status and host Ollama, then " + RETRY_COMMAND,
    )

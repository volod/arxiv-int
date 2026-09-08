"""CLI handlers for local inference health, identity, and schema generation."""

import argparse
import logging
from threading import Event

from arxiv_int.inference.client.factory import client_from_config
from arxiv_int.inference.client.transport import TransportError
from arxiv_int.inference.policy.schema import check_schema_drift, generate_schemas
from arxiv_int.runtime import ConfigurationError, load_runtime_config
from arxiv_int.runtime.project_root import ProjectRootError, find_project_root

_LOG = logging.getLogger(__name__)


def run_inference_command(args: argparse.Namespace, cancel: Event | None = None) -> int:
    """Dispatch `arxiv-int inference` subcommands."""
    try:
        if args.inference_command == "schemas":
            return _run_schemas(args)
        if args.inference_command == "resources":
            from arxiv_int.inference.scheduler.commands import run_scheduler_command

            return run_scheduler_command(args, None, cancel)
        root = find_project_root(args.project_root)
        config = load_runtime_config(project_root=root)
        if args.inference_command in {"fit", "schedule"}:
            from arxiv_int.inference.scheduler.commands import run_scheduler_command

            return run_scheduler_command(args, config, cancel)
        client = client_from_config(config, timeout=args.timeout)
        try:
            if args.inference_command == "health":
                return _run_health(client, cancel)
            if args.inference_command == "models":
                return _run_models(client, cancel)
            return _run_identity(client, args.model, cancel)
        finally:
            client.close()
    except (ConfigurationError, OSError, ProjectRootError, ValueError, TransportError) as error:
        _LOG.error("%s", error)
        return 1


def _run_schemas(args: argparse.Namespace) -> int:
    root = find_project_root(args.project_root)
    if args.schemas_command == "generate":
        files = generate_schemas(root)
        _LOG.info("generated %d structured-output schema(s)", len(files))
        return 0
    findings = check_schema_drift(root)
    if findings:
        for finding in findings:
            _LOG.error("%s", finding)
        return 1
    _LOG.info("structured-output schema drift check passed")
    return 0


def _run_health(client: object, cancel: Event | None) -> int:
    from arxiv_int.inference.client import LocalInferenceClient

    assert isinstance(client, LocalInferenceClient)
    status = client.health(cancel=cancel)
    if status.ready:
        _LOG.info("%s", status.detail)
        return 0
    _LOG.error("%s", status.detail)
    return 1


def _run_models(client: object, cancel: Event | None) -> int:
    from arxiv_int.inference.client import LocalInferenceClient

    assert isinstance(client, LocalInferenceClient)
    status = client.health(cancel=cancel)
    if not status.ready:
        _LOG.error("%s", status.detail)
        return 1
    for model in status.models:
        digest = model.digest or "-"
        caps = ",".join(sorted(model.capabilities)) or "-"
        _LOG.info("%s digest=%s capabilities=%s", model.model_id, digest, caps)
    return 0


def _run_identity(client: object, model_id: str | None, cancel: Event | None) -> int:
    from arxiv_int.inference.client import LocalInferenceClient

    assert isinstance(client, LocalInferenceClient)
    name = model_id or client.default_model
    if not name:
        _LOG.error("no generation model is configured")
        return 1
    identity = client.identify(name, cancel=cancel)
    caps = ",".join(sorted(identity.capabilities)) or "-"
    _LOG.info(
        "%s backend=%s digest=%s capabilities=%s",
        identity.model_id,
        identity.backend,
        identity.digest or "-",
        caps,
    )
    return 0


def default_cancel_event() -> Event:
    """Return a process-wide cancel event for SIGINT wiring."""
    return Event()

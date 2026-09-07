"""Local-only inference endpoint policy and secret-free outcome logging."""

import logging
from urllib.parse import urlsplit, urlunsplit

from arxiv_int.readiness.http_transport import local_base

_LOG = logging.getLogger("arxiv_int.inference")
PULL_PATH_MARKERS = ("/api/pull", "/v1/models/pull")


def canonical_local_url(value: str) -> str:
    """Return a loopback URL with localhost mapped to literal IPv4, or raise."""
    validated = local_base(value)
    if validated is None:
        raise ValueError("endpoint is not a local loopback URL")
    parsed = urlsplit(validated)
    host = "::1" if parsed.hostname == "::1" else "127.0.0.1"
    netloc = (
        f"[{host}]:{parsed.port}"
        if host == "::1" and parsed.port
        else (f"{host}:{parsed.port}" if parsed.port else host)
    )
    return urlunsplit((parsed.scheme, netloc, parsed.path or "/", "", "")).rstrip("/")


def is_pull_path(path: str) -> bool:
    """Report whether a request path would acquire model weights."""
    normalized = path.split("?", 1)[0].rstrip("/")
    return any(
        normalized.endswith(marker.rstrip("/")) or marker in normalized
        for marker in PULL_PATH_MARKERS
    )


def log_outcome(
    operation: str,
    *,
    backend: str,
    model_id: str,
    status: str,
    latency_seconds: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> None:
    """Log one inference outcome without prompt text, payloads, or secrets."""
    _LOG.info(
        "inference op=%s backend=%s model=%s status=%s latency_ms=%d prompt_tokens=%d completion_tokens=%d",
        operation,
        backend,
        model_id or "-",
        status,
        int(max(latency_seconds, 0.0) * 1000),
        prompt_tokens,
        completion_tokens,
    )

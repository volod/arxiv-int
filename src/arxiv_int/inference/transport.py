"""httpx transport bound to loopback, with timeouts, cancel polling, and size caps."""

import logging
from collections.abc import Iterator
from queue import Empty, Queue
from threading import Event, Thread
from time import monotonic
from typing import Any

from arxiv_int.features import require_module
from arxiv_int.inference.policy import canonical_local_url, is_pull_path

MAX_RESPONSE_BYTES = 8 * 1024 * 1024
READ_SLICE_SECONDS = 0.1
RETRY_STATUSES = frozenset({429, 502, 503, 504})
MAX_ATTEMPTS = 3
CONNECT_TIMEOUT_SECONDS = 5.0


class TransportError(RuntimeError):
    """A local inference HTTP call failed without exposing request payloads."""

    def __init__(self, status: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


def cancelled(cancel: Event | None) -> bool:
    """Report whether the caller requested cancellation."""
    return cancel is not None and cancel.is_set()


def retryable_status(status_code: int) -> bool:
    """Report whether an HTTP status should be retried."""
    return status_code in RETRY_STATUSES


def http_status_name(status_code: int) -> str:
    """Map an HTTP error to a typed inference status."""
    if status_code == 404:
        return "architecture_unsupported"
    return "backend_error"


class LocalHttpTransport:
    """POST/GET JSON and NDJSON/SSE streams against one validated local base URL."""

    def __init__(
        self, base_url: str, *, timeout: float, max_bytes: int = MAX_RESPONSE_BYTES
    ) -> None:
        if not timeout or timeout <= 0:
            raise ValueError("timeout must be positive")
        self.base_url = canonical_local_url(base_url)
        self.timeout = timeout
        self.max_bytes = max_bytes
        httpx = require_module("httpx")
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
        self._httpx = httpx
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            trust_env=False,
            follow_redirects=False,
        )

    def close(self) -> None:
        """Release the HTTP client."""
        self._client.close()

    def request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
        cancel: Event | None = None,
    ) -> tuple[int, object]:
        """Send one JSON request and return status plus parsed payload or empty mapping."""
        self._reject_pull(path)
        if cancelled(cancel):
            raise TransportError("cancelled", "request cancelled")
        timeout = timeout if timeout is not None else self.timeout
        try:
            response = self._client.request(
                method,
                path,
                json=payload,
                headers={"Accept": "application/json"},
                timeout=timeout,
            )
        except self._httpx.TimeoutException as error:
            raise TransportError("timeout", "local inference request timed out") from error
        except self._httpx.RequestError as error:
            raise TransportError("backend_error", _transport_detail(error)) from error
        return response.status_code, _read_json(response, self.max_bytes, response.status_code)

    def stream_lines(
        self,
        path: str,
        payload: dict[str, Any],
        *,
        timeout: float | None = None,
        cancel: Event | None = None,
    ) -> Iterator[str]:
        """Yield text lines from a streaming local POST until done, timeout, or cancel."""
        self._reject_pull(path)
        if cancelled(cancel):
            raise TransportError("cancelled", "request cancelled")
        timeout = timeout if timeout is not None else self.timeout
        deadline = monotonic() + timeout
        events: Queue[tuple[str, object]] = Queue()
        Thread(
            target=_stream_worker,
            args=(self._httpx, self._client, path, payload, timeout, events),
            daemon=True,
        ).start()
        byte_count = 0
        while True:
            kind, value = _next_event(events, deadline, cancel)
            if kind == "done":
                return
            text = _line_text(value)
            if text is None:
                continue
            byte_count += len(text.encode())
            if byte_count > self.max_bytes:
                raise TransportError("backend_error", "response too large")
            yield text

    def _reject_pull(self, path: str) -> None:
        if is_pull_path(path):
            raise TransportError("backend_error", "model acquisition is not an inference request")


def _stream_worker(
    httpx: Any,
    client: Any,
    path: str,
    payload: dict[str, Any],
    timeout: float,
    events: Queue[tuple[str, object]],
) -> None:
    http_timeout = httpx.Timeout(
        connect=min(CONNECT_TIMEOUT_SECONDS, timeout),
        read=timeout,
        write=timeout,
        pool=timeout,
    )
    try:
        with client.stream(
            "POST",
            path,
            json=payload,
            headers={"Accept": "application/json"},
            timeout=http_timeout,
        ) as response:
            if response.status_code >= 400:
                response.read()
                status_name = http_status_name(response.status_code)
                events.put(("error", TransportError(status_name, f"HTTP {response.status_code}")))
                return
            for line in response.iter_lines():
                events.put(("line", line))
        events.put(("done", None))
    except httpx.TimeoutException:
        events.put(("error", TransportError("timeout", "local inference request timed out")))
    except httpx.RequestError as error:
        events.put(("error", TransportError("backend_error", _transport_detail(error))))
    except OSError:
        events.put(("error", TransportError("backend_error", "local inference transport failed")))


def _next_event(
    events: Queue[tuple[str, object]], deadline: float, cancel: Event | None
) -> tuple[str, object]:
    while True:
        if cancelled(cancel):
            raise TransportError("cancelled", "request cancelled")
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TransportError("timeout", "local inference request timed out")
        try:
            kind, value = events.get(timeout=min(READ_SLICE_SECONDS, remaining))
        except Empty:
            continue
        if kind == "error":
            assert isinstance(value, TransportError)
            raise value
        return kind, value


def _line_text(value: object) -> str | None:
    if not value:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    return str(value)


def _read_json(response: Any, max_bytes: int, status_code: int) -> object:
    content = response.content
    if len(content) > max_bytes:
        raise TransportError("backend_error", "response too large")
    if not content:
        return {}
    try:
        return response.json()
    except ValueError as error:
        if status_code >= 400:
            raise TransportError(http_status_name(status_code), f"HTTP {status_code}") from error
        raise TransportError("malformed", "response was not JSON") from error


def _transport_detail(error: BaseException) -> str:
    name = error.__class__.__name__
    if "connect" in name.lower() or "connect" in str(error).lower():
        return "local inference endpoint is unreachable"
    return "local inference transport failed"

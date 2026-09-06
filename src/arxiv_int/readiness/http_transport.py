"""Local-only HTTP transport with bounded bodies and a socket deadline."""

import json
import math
import socket
from contextlib import suppress
from http.client import HTTPConnection, HTTPSConnection
from threading import Timer
from time import monotonic
from urllib.parse import urlsplit, urlunsplit

MAX_RESPONSE_BYTES = 1024 * 1024


def local_base(value: str) -> str | None:
    """Validate without echoing credentials or accepting ambiguous URL authorities."""
    try:
        parsed = urlsplit(value)
        valid = (
            parsed.scheme in {"http", "https"}
            and parsed.hostname in {"127.0.0.1", "localhost", "::1"}
            and parsed.username is None
            and parsed.password is None
            and (parsed.port is None or 0 < parsed.port < 65536)
            and not parsed.query
            and not parsed.fragment
            and not any(ord(char) <= 32 or ord(char) == 127 for char in value)
        )
    except ValueError:
        return None
    return value.rstrip("/") + "/" if valid else None


def _shutdown(stream: socket.socket) -> None:
    with suppress(OSError):
        stream.shutdown(socket.SHUT_RDWR)


def fetch_json(url: str, *, timeout: float) -> tuple[int, object | None]:
    """Connect directly to loopback, without proxies or redirects, and cap response bytes."""
    if local_base(url) is None or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("invalid local request")
    parsed = urlsplit(url)
    # Resolve localhost to a literal, so host resolution cannot send the probe elsewhere.
    host = "::1" if parsed.hostname == "::1" else "127.0.0.1"
    factory = HTTPSConnection if parsed.scheme == "https" else HTTPConnection
    connection = factory(host, parsed.port, timeout=timeout)
    deadline = monotonic() + timeout
    timer: Timer | None = None
    try:
        connection.connect()
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise TimeoutError
        assert connection.sock is not None
        timer = Timer(remaining, _shutdown, (connection.sock,))
        timer.daemon = True
        timer.start()
        path = urlunsplit(("", "", parsed.path or "/", "", ""))
        connection.request("GET", path, headers={"Accept": "application/json"})
        with connection.getresponse() as response:
            if response.status != 200:
                return response.status, None
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if monotonic() >= deadline:
                raise TimeoutError
            if len(body) > MAX_RESPONSE_BYTES:
                raise ValueError("response too large")
            return response.status, json.loads(body)
    finally:
        if timer is not None:
            timer.cancel()
            timer.join()
        connection.close()

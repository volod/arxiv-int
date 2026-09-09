"""Assemble provider stream lines into one completion without logging payloads."""

import json
from collections.abc import Callable
from threading import Event

from arxiv_int.inference.client.transport import LocalHttpTransport, TransportError
from arxiv_int.inference.client.types import StreamChunk

SSE_DONE = "[DONE]"


def decode_line(line: str) -> dict[str, object] | None:
    """Parse one NDJSON or SSE `data:` line into a JSON object."""
    stripped = line.strip()
    if not stripped or stripped == SSE_DONE:
        return None
    if stripped.startswith("data:"):
        stripped = stripped[5:].strip()
        if not stripped or stripped == SSE_DONE:
            return None
    try:
        payload = json.loads(stripped)
    except json.JSONDecodeError as error:
        raise TransportError("malformed", "stream line was not JSON") from error
    if not isinstance(payload, dict):
        raise TransportError("malformed", "stream line was not an object")
    return payload


def collect_text(
    transport: LocalHttpTransport,
    path: str,
    payload: dict[str, object],
    parse_chunk: Callable[[dict[str, object]], StreamChunk],
    *,
    timeout: float | None,
    cancel: Event | None,
) -> tuple[str, StreamChunk]:
    """Read a stream to completion and return concatenated text plus the last chunk."""
    pieces: list[str] = []
    last = StreamChunk(text="", done=True)
    for line in transport.stream_lines(path, payload, timeout=timeout, cancel=cancel):
        decoded = decode_line(line)
        if decoded is None:
            continue
        chunk = parse_chunk(decoded)
        if chunk.text:
            pieces.append(chunk.text)
        last = chunk
    return "".join(pieces), last

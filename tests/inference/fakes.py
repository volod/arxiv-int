"""In-process Ollama and vLLM loopback fakes for deterministic inference tests."""

import json
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import sleep
from typing import Any

from arxiv_int.inference.policy.schema import CITED_SPAN_SCHEMA

VALID_SPAN = '{"value":"alpha","evidence":[{"quote":"alpha","start":0,"end":5}]}'
INVALID_SPAN = '{"value":""}'
REFUSAL_JSON = '{"status":"refused","reason":"not enough evidence"}'
CHAT_TEXT = "hello from fixture"


@dataclass
class FakeState:
    """Mutable fake-provider behavior for one test."""

    models: list[dict[str, Any]]
    delay: float = 0.0
    fail_remaining: int = 0
    invalid_structured_remaining: int = 0
    refuse: bool = False
    pull_count: int = 0
    requests: list[tuple[str, str]] = field(default_factory=list)
    loaded: list[str] = field(default_factory=list)
    loaded_vram: int = 2 * 1024**3
    chat_text: str = CHAT_TEXT


def default_models(backend: str) -> list[dict[str, Any]]:
    """Return chat and embedding identities for one backend."""
    if backend == "ollama":
        return [
            {
                "name": "fixture-chat",
                "digest": "sha256:chat",
                "capabilities": ["completion"],
            },
            {
                "name": "fixture-embed",
                "digest": "sha256:embed",
                "capabilities": ["embedding"],
            },
        ]
    return [
        {"id": "fixture-chat", "root": "rev-chat"},
        {"id": "fixture-embed", "root": "rev-embed"},
    ]


@contextmanager
def serve(backend: str, state: FakeState | None = None) -> Iterator[str]:
    """Serve one backend on an ephemeral loopback port."""
    current = state or FakeState(models=default_models(backend))
    handler = type("Handler", (FakeHandler,), {"backend": backend, "state": current})
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


class FakeHandler(BaseHTTPRequestHandler):
    """Loopback Ollama/vLLM stand-in. Subclasses set backend and state."""

    protocol_version = "HTTP/1.1"
    backend = "ollama"
    state = FakeState(models=[])

    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        _dispatch(self, "GET", None)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        payload = json.loads(raw.decode("utf-8") or "{}")
        _dispatch(self, "POST", payload if isinstance(payload, dict) else {})

    def send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(body)


def _dispatch(handler: FakeHandler, method: str, payload: dict[str, Any] | None) -> None:
    path = handler.path.split("?", 1)[0]
    handler.state.requests.append((method, path))
    if path.rstrip("/").endswith("/pull") or path == "/api/pull":
        handler.state.pull_count += 1
        handler.send_json(404, {"error": "pull is not served"})
        return
    if _handle_read(handler, method, path):
        return
    if method == "POST":
        _handle_write(handler, path, payload or {})
        return
    handler.send_json(404, {"error": "not found"})


def _handle_read(handler: FakeHandler, method: str, path: str) -> bool:
    if method == "GET" and path in {"/api/tags", "/v1/models"}:
        handler.send_json(200, _model_list(handler.backend, handler.state))
        return True
    if method == "GET" and path in {"/", "/health"}:
        handler.send_json(200, {"status": "ok"})
        return True
    if method == "GET" and path.rstrip("/").endswith("/api/ps"):
        models = [
            {"name": name, "size_vram": handler.state.loaded_vram} for name in handler.state.loaded
        ]
        handler.send_json(200, {"models": models})
        return True
    return False


def _handle_write(handler: FakeHandler, path: str, payload: dict[str, Any]) -> None:
    if path == "/api/show":
        _send_show(handler, payload)
        return
    if path in {"/api/chat", "/api/generate", "/v1/chat/completions"}:
        _send_completion(handler, payload)
        return
    if path in {"/api/embed", "/v1/embeddings"}:
        _send_embed(handler, payload)
        return
    handler.send_json(404, {"error": "not found"})


def _send_show(handler: FakeHandler, payload: dict[str, Any]) -> None:
    model_id = str(payload.get("model") or "")
    item = _find_model(handler.backend, handler.state, model_id)
    if item is None:
        handler.send_json(404, {"error": f"model '{model_id}' not found"})
        return
    capabilities = item.get("capabilities") or ["completion"]
    handler.send_json(200, {"capabilities": capabilities, "digest": item.get("digest", "")})


def _send_completion(handler: FakeHandler, payload: dict[str, Any]) -> None:
    if handler.state.delay:
        sleep(handler.state.delay)
    if handler.state.fail_remaining > 0:
        handler.state.fail_remaining -= 1
        handler.send_json(503, {"error": "busy"})
        return
    model_id = str(payload.get("model") or "")
    if payload.get("keep_alive") in {0, "0"}:
        handler.state.loaded = [name for name in handler.state.loaded if name != model_id]
        handler.send_json(200, {"done": True})
        return
    if _find_model(handler.backend, handler.state, model_id) is None:
        handler.send_json(404, {"error": f"model '{model_id}' not found"})
        return
    if model_id not in handler.state.loaded:
        handler.state.loaded.append(model_id)
    _stream(handler, handler.backend, model_id, _completion_text(handler.state, payload))


def _send_embed(handler: FakeHandler, payload: dict[str, Any]) -> None:
    model_id = str(payload.get("model") or "")
    item = _find_model(handler.backend, handler.state, model_id)
    if item is None:
        handler.send_json(404, {"error": f"model '{model_id}' not found"})
        return
    if handler.backend == "ollama" and "embedding" not in (item.get("capabilities") or []):
        handler.send_json(400, {"error": "model does not support embeddings"})
        return
    texts = payload.get("input") or payload.get("prompt") or []
    if isinstance(texts, str):
        texts = [texts]
    vectors = [[float(len(text)), 1.0] for text in texts]
    if handler.backend == "ollama":
        handler.send_json(200, {"embeddings": vectors})
        return
    data = [{"index": index, "embedding": vector} for index, vector in enumerate(vectors)]
    handler.send_json(200, {"data": data})


def _stream(handler: FakeHandler, current_backend: str, model_id: str, content: str) -> None:
    handler.send_response(200)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Connection", "close")
    handler.end_headers()
    try:
        handler.wfile.write(_stream_body(current_backend, model_id, content))
        handler.wfile.flush()
    except OSError:
        return


def _stream_body(current_backend: str, model_id: str, content: str) -> bytes:
    if current_backend == "ollama":
        first = json.dumps(
            {"model": model_id, "message": {"role": "assistant", "content": content}, "done": False}
        )
        last = json.dumps(
            {
                "model": model_id,
                "message": {"role": "assistant", "content": ""},
                "done": True,
                "done_reason": "stop",
                "prompt_eval_count": 3,
                "eval_count": 2,
            }
        )
        return f"{first}\n{last}\n".encode()
    chunk = json.dumps(
        {
            "model": model_id,
            "choices": [{"delta": {"content": content}, "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }
    )
    return f"data: {chunk}\ndata: [DONE]\n".encode()


def _model_list(backend: str, state: FakeState) -> dict[str, Any]:
    if backend == "ollama":
        return {"models": state.models}
    return {"data": state.models}


def _find_model(backend: str, state: FakeState, model_id: str) -> dict[str, Any] | None:
    key = "name" if backend == "ollama" else "id"
    for item in state.models:
        if item.get(key) == model_id:
            return item
    return None


def _completion_text(state: FakeState, payload: dict[str, Any]) -> str:
    structured = payload.get("format") == CITED_SPAN_SCHEMA or (
        isinstance(payload.get("response_format"), dict)
    )
    if state.refuse and structured:
        return REFUSAL_JSON
    if structured:
        if state.invalid_structured_remaining > 0:
            state.invalid_structured_remaining -= 1
            return INVALID_SPAN
        return VALID_SPAN
    return state.chat_text

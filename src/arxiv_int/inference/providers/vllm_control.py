"""Optional Compose start/stop for the vLLM profile when the caller requested it."""

from http.client import HTTPException

from arxiv_int.inference.client.errors import ModelFitError
from arxiv_int.inference.policy import canonical_local_url
from arxiv_int.readiness.http_transport import fetch_json
from arxiv_int.runtime.compose import run_compose
from arxiv_int.runtime.config_model import RuntimeConfig
from arxiv_int.runtime.inference_config import VLLM_DEFAULT_PORT


class ComposeVllmController:
    """Start or stop only the vLLM Compose service on an explicit request."""

    def __init__(self, config: RuntimeConfig, *, timeout: float = 3.0) -> None:
        self._config = config
        values = dict(config.values)
        port = values.get("VLLM_PORT", "").strip() or VLLM_DEFAULT_PORT
        self._health_url = canonical_local_url(f"http://127.0.0.1:{port}") + "/health"
        self._timeout = timeout

    def start(self) -> None:
        status = run_compose(self._config, "up", "vllm", services=("vllm",))
        if status != 0:
            raise ModelFitError("vLLM Compose up failed")

    def stop(self) -> None:
        status = run_compose(self._config, "down", "vllm", services=("vllm",))
        if status != 0:
            raise ModelFitError("vLLM Compose down failed")

    def ready(self) -> bool:
        try:
            status, _payload = fetch_json(self._health_url, timeout=self._timeout)
        except (OSError, ValueError, RecursionError, HTTPException):
            return False
        return status == 200

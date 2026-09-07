"""Declared CUDA-host smoke against a running local Ollama service."""

import os

import pytest

from arxiv_int.inference.factory import client_from_config
from arxiv_int.inference.schema import CITED_SPAN_SCHEMA
from arxiv_int.interfaces.inference import GenerationRequest
from arxiv_int.runtime import load_runtime_config

pytestmark = pytest.mark.skipif(
    os.environ.get("ARXIV_INT_RUN_INFERENCE_SMOKE") != "1",
    reason="set ARXIV_INT_RUN_INFERENCE_SMOKE=1 for the declared local Ollama smoke",
)


def test_host_ollama_health_chat_and_structured_output() -> None:
    config = load_runtime_config()
    client = client_from_config(config, timeout=120.0)
    try:
        health = client.health()
        assert health.ready, health.detail
        models = set(client.available_models())
        model_id = (
            "llama3.2:3b"
            if "llama3.2:3b" in models
            else (client.default_model or next(iter(models)))
        )
        identity = client.identify(model_id)
        assert identity.model_id == model_id
        chat = client.generate(
            GenerationRequest(
                "Reply with the single word pong.", model_id=model_id, max_output_tokens=16
            )
        )
        assert chat.status == "ok", chat.text
        assert chat.model_digest or identity.digest
        structured = client.generate(
            GenerationRequest(
                "Return JSON with value 'ok' and one evidence quote 'ok' from start 0 end 2.",
                model_id=model_id,
                json_schema=CITED_SPAN_SCHEMA,
                schema_version="cited-span",
                max_output_tokens=128,
            )
        )
        assert structured.status in {"ok", "malformed", "refused"}
    finally:
        client.close()

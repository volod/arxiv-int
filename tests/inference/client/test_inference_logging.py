"""Prompt and secret text must not appear in inference logs."""

import logging

import pytest

pytest.importorskip("httpx")

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.interfaces.inference import GenerationRequest
from tests.inference.fakes import serve


def test_generate_logs_do_not_include_prompt_or_secrets(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    with serve("ollama") as base_url:
        client = LocalInferenceClient(
            "ollama",
            base_url,
            default_model="fixture-chat",
            timeout=2.0,
        )
        try:
            result = client.generate(GenerationRequest("fixture-secret-prompt"))
            assert result.status == "ok"
        finally:
            client.close()
    combined = caplog.text
    assert "fixture-secret-prompt" not in combined
    assert "status=ok" in combined

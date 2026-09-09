"""Provider conformance for Ollama and vLLM against in-process fake servers."""

from threading import Event, Thread
from time import sleep

import pytest

pytest.importorskip("httpx")

from arxiv_int.inference.client import LocalInferenceClient
from arxiv_int.inference.client.types import EmbeddingRequest
from arxiv_int.inference.policy.schema import CITED_SPAN_SCHEMA
from arxiv_int.interfaces.inference import ChatMessage, GenerationRequest, InferenceProvider
from tests.inference.fakes import FakeState, default_models, serve

BACKENDS = ("ollama", "vllm")


def _client(backend: str, base_url: str, **kwargs: object) -> LocalInferenceClient:
    return LocalInferenceClient(
        backend,
        base_url,
        default_model="fixture-chat",
        embedding_model="fixture-embed",
        timeout=2.0,
        **kwargs,
    )


@pytest.mark.parametrize("backend", BACKENDS)
def test_providers_agree_on_health_chat_and_identity(backend: str) -> None:
    with serve(backend) as base_url:
        client = _client(backend, base_url)
        try:
            assert isinstance(client, InferenceProvider)
            health = client.health()
            assert health.ready
            assert "fixture-chat" in client.available_models()
            identity = client.identify("fixture-chat")
            assert identity.digest
            chat = client.chat([ChatMessage("user", "secret-prompt")])
            generate = client.generate(GenerationRequest("secret-prompt"))
            assert chat.status == generate.status == "ok"
            assert chat.text == generate.text == "hello from fixture"
            assert chat.model_digest or identity.digest
            assert chat.tokens_per_second >= 0
        finally:
            client.close()


@pytest.mark.parametrize("backend", BACKENDS)
def test_structured_output_repairs_then_passes(backend: str) -> None:
    state = FakeState(models=default_models(backend), invalid_structured_remaining=1)
    with serve(backend, state) as base_url:
        client = _client(backend, base_url)
        try:
            result = client.generate(
                GenerationRequest(
                    "secret-prompt", json_schema=CITED_SPAN_SCHEMA, schema_version="cited-span"
                )
            )
            assert result.status == "ok"
            assert "alpha" in result.text
        finally:
            client.close()


@pytest.mark.parametrize("backend", BACKENDS)
def test_structured_output_exhausts_repair_as_malformed(backend: str) -> None:
    state = FakeState(models=default_models(backend), invalid_structured_remaining=5)
    with serve(backend, state) as base_url:
        client = _client(backend, base_url)
        try:
            result = client.generate(
                GenerationRequest("secret-prompt", json_schema=CITED_SPAN_SCHEMA)
            )
            assert result.status == "malformed"
        finally:
            client.close()


@pytest.mark.parametrize("backend", BACKENDS)
def test_refusal_is_a_typed_status(backend: str) -> None:
    state = FakeState(models=default_models(backend), refuse=True)
    with serve(backend, state) as base_url:
        client = _client(backend, base_url)
        try:
            result = client.generate(
                GenerationRequest("secret-prompt", json_schema=CITED_SPAN_SCHEMA)
            )
            assert result.status == "refused"
        finally:
            client.close()


@pytest.mark.parametrize("backend", BACKENDS)
def test_missing_and_embedding_mismatch_are_architecture_unsupported(backend: str) -> None:
    with serve(backend) as base_url:
        client = _client(backend, base_url)
        try:
            missing = client.generate(GenerationRequest("secret-prompt", model_id="missing-model"))
            assert missing.status == "architecture_unsupported"
            chat_as_embed = client.embed(EmbeddingRequest(("hello",), model_id="fixture-chat"))
            assert chat_as_embed.status == "architecture_unsupported"
            embedded = client.embed(EmbeddingRequest(("hello", "world")))
            assert embedded.status == "ok"
            assert embedded.dimensions == 2
            assert len(embedded.vectors) == 2
        finally:
            client.close()


@pytest.mark.parametrize("backend", BACKENDS)
def test_timeout_cancel_retry_and_unreachable_statuses(backend: str) -> None:
    state = FakeState(models=default_models(backend), delay=1.0)
    with serve(backend, state) as base_url:
        slow = _client(backend, base_url)
        slow.timeout = 0.25
        try:
            timed = slow.generate(GenerationRequest("secret-prompt"))
            assert timed.status == "timeout"
        finally:
            slow.close()
        cancel_state = FakeState(models=default_models(backend), delay=1.0)
        with serve(backend, cancel_state) as cancel_url:
            cancellable = _client(backend, cancel_url)
            try:
                cancel = Event()

                def _trip() -> None:
                    sleep(0.15)
                    cancel.set()

                Thread(target=_trip, daemon=True).start()
                cancelled = cancellable.generate(GenerationRequest("secret-prompt"), cancel)
                assert cancelled.status == "cancelled"
            finally:
                cancellable.close()
        retry_state = FakeState(models=default_models(backend), fail_remaining=2)
        with serve(backend, retry_state) as retry_url:
            retry_client = _client(backend, retry_url)
            try:
                recovered = retry_client.generate(GenerationRequest("secret-prompt"))
                assert recovered.status == "ok"
            finally:
                retry_client.close()
    missing = LocalInferenceClient(backend, "http://127.0.0.1:1", timeout=0.2, default_model="x")
    try:
        health = missing.health()
        assert not health.ready
        assert "unreachable" in health.detail or health.detail
        failed = missing.generate(GenerationRequest("secret-prompt"))
        assert failed.status in {"backend_error", "timeout"}
    finally:
        missing.close()


@pytest.mark.parametrize("backend", BACKENDS)
def test_inference_never_pulls_models(backend: str) -> None:
    state = FakeState(models=default_models(backend))
    with serve(backend, state) as base_url:
        client = _client(backend, base_url)
        try:
            client.health()
            client.generate(GenerationRequest("secret-prompt"))
            client.embed(EmbeddingRequest(("hello",)))
        finally:
            client.close()
    assert state.pull_count == 0
    assert all("/pull" not in path for _, path in state.requests)


@pytest.mark.parametrize("backend", BACKENDS)
def test_generate_records_requested_identity_and_refuses_unknown_models(backend: str) -> None:
    with serve(backend) as base_url:
        client = _client(backend, base_url)
        try:
            identity = client.identify("fixture-chat")
            result = client.generate(GenerationRequest("secret-prompt", model_id="fixture-chat"))
            assert result.status == "ok"
            assert result.model_id == "fixture-chat"
            assert result.model_digest == identity.digest
            missing = client.generate(GenerationRequest("secret-prompt", model_id="swapped-chat"))
            assert missing.status == "architecture_unsupported"
            assert missing.model_id == "swapped-chat"
        finally:
            client.close()

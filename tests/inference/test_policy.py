"""Local-only endpoint policy and redaction helpers."""

import pytest

from arxiv_int.inference.policy import canonical_local_url, is_pull_path, log_outcome


def test_loopback_urls_are_canonicalized_to_literal_ipv4() -> None:
    assert canonical_local_url("http://localhost:11434") == "http://127.0.0.1:11434"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com:11434",
        "http://user:fixture-secret@127.0.0.1:11434",
        "http://127.0.0.1:11434/?token=fixture-secret",
        "http://127.0.0.1:11434/#frag",
        "https://8.8.8.8/v1",
    ],
)
def test_remote_or_credential_urls_are_rejected(url: str) -> None:
    with pytest.raises(ValueError, match="local loopback"):
        canonical_local_url(url)


def test_pull_paths_are_recognized() -> None:
    assert is_pull_path("/api/pull")
    assert not is_pull_path("/api/chat")


def test_outcome_logs_omit_prompt_text(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level("INFO", logger="arxiv_int.inference")
    log_outcome(
        "generate",
        backend="ollama",
        model_id="fixture-chat",
        status="ok",
        latency_seconds=0.5,
        prompt_tokens=3,
        completion_tokens=2,
    )
    assert "secret-prompt" not in caplog.text
    assert "fixture-secret" not in caplog.text
    assert "status=ok" in caplog.text

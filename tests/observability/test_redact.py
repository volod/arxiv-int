"""Redaction removes secrets, prompts, paths, and corpus text."""

from arxiv_int.observability.redact import redact_mapping, redact_text, shard_token


def test_redact_text_strips_secrets_prompts_paths_and_long_quotes() -> None:
    raw = (
        "password=super-secret token=abcd DATABASE_URL=postgresql://u:hunter2@127.0.0.1/db "
        "prompt=the full operator prompt goes here "
        "/home/vola/archive/doc.pdf "
        '"' + ("corpus " * 60) + '"'
    )
    redacted = redact_text(raw, extra_secrets=("super-secret",))
    assert "super-secret" not in redacted
    assert "hunter2" not in redacted
    assert "the full operator prompt" not in redacted
    assert "/home/vola" not in redacted
    assert "corpus " not in redacted or "<redacted" in redacted
    assert "<redacted>" in redacted
    assert "<path>" in redacted


def test_redact_mapping_blocks_document_fields() -> None:
    payload = redact_mapping(
        {"prompt": "secret prompt", "stage": "extract", "text": "document body"}
    )
    assert payload["prompt"] == "<redacted>"
    assert payload["text"] == "<redacted>"
    assert payload["stage"] == "extract"


def test_shard_token_is_short_and_not_a_path() -> None:
    assert shard_token("default") == "default"
    assert shard_token("/tmp/archive/very-long-document-identifier.pdf") == "very-lon"
    assert "/" not in shard_token("/tmp/archive/doc.pdf")


def test_extra_secrets_from_env_collects_credential_values() -> None:
    from arxiv_int.observability.redact import extra_secrets_from_env

    secrets = extra_secrets_from_env(
        {"POSTGRES_PASSWORD": "s3cret", "DATABASE_URL": "postgresql://u:p@h/db", "OTHER": "x"}
    )
    assert "s3cret" in secrets
    assert "postgresql://u:p@h/db" in secrets
    assert "x" not in secrets

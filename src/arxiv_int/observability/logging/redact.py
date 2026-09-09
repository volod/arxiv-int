"""Strip secrets, prompts, corpus text, and filesystem paths from operator logs."""

import os
import re
from collections.abc import Iterable, Mapping

from arxiv_int.observability.metrics.constants import MAX_DETAIL_CHARS, MAX_SHARD_TOKEN_LEN

_SECRET_ENV_NAMES = (
    "POSTGRES_PASSWORD",
    "DATABASE_URL",
    "ARXIV_INT_MIGRATION_DATABASE_URL",
    "ARXIV_INT_TRANSFORM_DATABASE_URL",
    "HF_TOKEN",
)

_SECRET_ASSIGN = re.compile(
    r"(?i)\b(password|secret|token|api[_-]?key|authorization|bearer)\b\s*[=:]\s*\S+"
)
_POSTGRES_URL = re.compile(r"(?i)(postgres(?:ql)?(?:\+\w+)?://[^:\s/]+):([^@\s]+)@")
_ABS_PATH = re.compile(r"(?:(?:[A-Za-z]:)?/(?:home|Users|var|opt|tmp|mnt|data)/[^\s,;]+)")
_PROMPT_ASSIGN = re.compile(
    r"(?i)\b(prompt|system_prompt|user_message|corpus_text)\b\s*[=:]\s*"
    r"(?:(?!/(?:home|Users|var|opt|tmp|mnt|data)/)[^\"\n])+"
)
_LONG_QUOTE = re.compile(r'"[^"]{241,}"')


def shard_token(value: str) -> str:
    """Return a short operational shard token, never a full document id or path."""
    token = value.strip().replace("\\", "/").rsplit("/", 1)[-1]
    if len(token) <= MAX_SHARD_TOKEN_LEN:
        return token or "default"
    return token[:8]


def extra_secrets_from_env(environ: Mapping[str, str] | None = None) -> tuple[str, ...]:
    """Collect credential values to redact; never log the returned strings."""
    source = os.environ if environ is None else environ
    values: list[str] = []
    for name in _SECRET_ENV_NAMES:
        value = source.get(name, "").strip()
        if value:
            values.append(value)
    return tuple(values)


def redact_text(text: str, extra_secrets: Iterable[str] = ()) -> str:
    """Replace credentials, prompts, absolute paths, and long quoted corpus text."""
    redacted = text
    for secret in extra_secrets:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    redacted = _POSTGRES_URL.sub(r"\1:<redacted>@", redacted)
    redacted = _SECRET_ASSIGN.sub(lambda match: f"{match.group(1)}=<redacted>", redacted)
    redacted = _PROMPT_ASSIGN.sub(lambda match: f"{match.group(1)}=<redacted>", redacted)
    redacted = _ABS_PATH.sub("<path>", redacted)
    redacted = _LONG_QUOTE.sub('"<redacted-text>"', redacted)
    if len(redacted) > MAX_DETAIL_CHARS:
        return redacted[:MAX_DETAIL_CHARS] + "...<truncated>"
    return redacted


def redact_mapping(
    payload: Mapping[str, object], extra_secrets: Iterable[str] = ()
) -> dict[str, object]:
    """Copy a mapping with string values passed through ``redact_text``."""
    blocked = {"prompt", "text", "document", "body", "password", "secret", "token"}
    result: dict[str, object] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if lowered in blocked:
            result[key] = "<redacted>"
            continue
        if isinstance(value, str):
            result[key] = redact_text(value, extra_secrets)
        else:
            result[key] = value
    return result

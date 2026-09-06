"""Sanitize dbt artifacts and compute selected-model fingerprints."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import sha256_text
from arxiv_int.contracts.migrations.runner import redact_url
from arxiv_int.data_quality.model import is_sensitive_column

_DROP_KEYS = frozenset({"env", "password", "credentials", "credential", "secret", "token"})


def sanitize_value(value: Any) -> Any:
    """Drop env dumps and redact credential-bearing strings recursively."""
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_value(item)
            for key, item in value.items()
            if str(key).lower() not in _DROP_KEYS and not is_sensitive_column(str(key))
        }
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str):
        return redact_url(value)
    return value


def load_json(path: Path) -> dict[str, Any]:
    """Load one JSON object or return an empty mapping when the file is absent."""
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def write_sanitized_json(source: Path, destination: Path) -> Path:
    """Write a secret-free copy of one dbt JSON artifact."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    payload = sanitize_value(load_json(source))
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return destination


def sanitize_text(content: str, secrets: tuple[str, ...] = ()) -> str:
    """Redact database URLs and known secret substrings from retained text."""
    redacted = redact_url(content)
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


def sanitize_log_files(log_dir: Path, secrets: tuple[str, ...] = ()) -> None:
    """Rewrite dbt log files in place without credentials."""
    if not log_dir.is_dir():
        return
    for path in log_dir.rglob("*"):
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        path.write_text(sanitize_text(text, secrets), encoding="utf-8")


def compiled_sql_fingerprint(target_dir: Path) -> str:
    """Fingerprint compiled SQL for selected models in stable path order."""
    compiled = target_dir / "compiled"
    if not compiled.is_dir():
        return sha256_text("")
    parts: list[str] = []
    for path in sorted(compiled.rglob("*.sql")):
        relative = path.relative_to(compiled).as_posix()
        parts.append(f"{relative}:{sha256_text(path.read_text(encoding='utf-8'))}")
    return sha256_text("|".join(parts))


def input_fingerprint(
    *,
    command: str,
    generation_id: str,
    policy_version: str,
    select: tuple[str, ...],
    full_refresh: bool,
) -> str:
    """Fingerprint invocation inputs without embedding paths or secrets."""
    selected = ",".join(select)
    refresh = "full" if full_refresh else "incremental"
    return sha256_text(f"{command}|{generation_id}|{policy_version}|{selected}|{refresh}")


def relation_names(generation_id: str) -> tuple[str, ...]:
    """Return isolated derived relation identities for the fixture DAG."""
    suffix = f"__g_{generation_id}"
    return (
        f"derived.stg_documents{suffix}",
        f"derived.int_documents_current{suffix}",
        f"derived.documents_current{suffix}",
    )


def rule_outcomes_from_run_results(payload: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Extract secret-free test/model outcomes from sanitized run results."""
    results: list[dict[str, Any]] = []
    for item in payload.get("results") or ():
        if not isinstance(item, Mapping):
            continue
        unique_id = str(item.get("unique_id") or item.get("node") or "")
        status = str(item.get("status") or "")
        message = redact_url(str(item.get("message") or ""))
        results.append(
            {
                "uniqueId": unique_id,
                "status": status,
                "message": message,
                "failures": item.get("failures"),
            }
        )
    return tuple(results)

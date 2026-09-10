"""Typed policy, inputs, and failures for text normalization."""

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path

from arxiv_int.pipeline.normalize.text import ALGORITHM_VERSION


@dataclass(frozen=True, slots=True)
class NormalizePolicy:
    """Explicit bounds and thresholds for one normalization producer."""

    batch_rows: int = 256
    max_document_chars: int = 20_000_000
    language_sample_chars: int = 20_000
    min_language_letters: int = 40
    min_language_confidence: float = 0.30


DEFAULT_POLICY = NormalizePolicy()


@dataclass(frozen=True, slots=True)
class DocumentInput:
    """One extracted document offered to normalization."""

    document_id: str
    content_hash: str
    text_sha256: str
    media_type: str
    title: str
    text_chars: int
    text_path: Path


class NormalizationError(RuntimeError):
    """One actionable per-document normalization failure."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def normalizer_id(policy: NormalizePolicy, profile_fingerprint: str) -> str:
    """Return the stable identity of one normalization algorithm and policy."""
    payload = json.dumps(
        {
            "algorithm": ALGORITHM_VERSION,
            "policy": asdict(policy),
            "profiles": profile_fingerprint,
        },
        ensure_ascii=True,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()[:32]


def normalized_document_id(document_id: str, normalizer: str) -> str:
    """Derive a stable normalized-document identity from its inputs."""
    value = f"normalized-document:{document_id}:{normalizer}"
    return hashlib.sha256(value.encode("ascii")).hexdigest()

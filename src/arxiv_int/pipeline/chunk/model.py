"""Typed policy, records, and identities for source-aligned chunking."""

import hashlib
import json
from dataclasses import asdict, dataclass, field

ALGORITHM_VERSION = "1"
TEXT_CHUNK = "text"
TABLE_CHUNK = "table"


@dataclass(frozen=True, slots=True)
class ChunkPolicy:
    """Explicit bounds for one deterministic chunk producer."""

    batch_rows: int = 256
    target_chars: int = 1200
    max_chars: int = 2400
    min_chars: int = 200
    overlap_sentences: int = 1
    heading_max_chars: int = 120
    table_min_rows: int = 2
    max_document_chunks: int = 20_000

    def __post_init__(self) -> None:
        if not 0 < self.min_chars <= self.target_chars <= self.max_chars:
            raise ValueError("chunk size bounds must be ordered and positive")
        if self.overlap_sentences < 0:
            raise ValueError("overlap_sentences must not be negative")


DEFAULT_POLICY = ChunkPolicy()


@dataclass(frozen=True, slots=True)
class Block:
    """One classified region of canonical text."""

    kind: str
    start: int
    end: int
    text: str
    level: int = 0


@dataclass(frozen=True, slots=True)
class Chunk:
    """One emitted chunk, aligned to the canonical text it came from."""

    ordinal: int
    kind: str
    text: str
    start: int
    end: int
    section_path: tuple[str, ...] = ()
    prefix_chars: int = 0
    prefix_span: tuple[int, int] | None = None
    sentences: int = 0


@dataclass(slots=True)
class DocumentChunks:
    """Every chunk of one document plus the counters reported as evidence."""

    chunks: list[Chunk] = field(default_factory=list)
    truncated: bool = False


class ChunkingError(Exception):
    """Raised when one document cannot be chunked and must be quarantined."""

    def __init__(self, reason: str, detail: str) -> None:
        super().__init__(f"{reason}: {detail}")
        self.reason = reason
        self.detail = detail


def chunker_id(policy: ChunkPolicy) -> str:
    """Return the stable identity of one chunking algorithm and policy."""
    payload = json.dumps(
        {"algorithm": ALGORITHM_VERSION, "policy": asdict(policy)},
        ensure_ascii=True,
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode("ascii")).hexdigest()[:32]


def chunk_id(document_id: str, chunker: str, chunk: Chunk) -> str:
    """Derive a stable chunk identity from its document, policy, and span."""
    value = f"chunk:{document_id}:{chunker}:{chunk.kind}:{chunk.start}:{chunk.end}:{chunk.ordinal}"
    return hashlib.sha256(value.encode("ascii")).hexdigest()

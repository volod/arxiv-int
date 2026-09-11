"""Typed inputs and results for Russian lexical calibration."""

from dataclasses import dataclass
from pathlib import Path

from arxiv_int.evaluation.scoring.paired import PairedComparison
from arxiv_int.retrieval.metrics import RetrievalMetrics


@dataclass(frozen=True, slots=True)
class CalibrationChunk:
    """One synthetic, source-safe chunk shared by every compared index."""

    chunk_id: str
    document_id: str
    title: str
    body: str
    identifiers: str
    language: str


@dataclass(frozen=True, slots=True)
class CalibrationCase:
    """One frozen query and its relevant chunk identities."""

    case_id: str
    category: str
    split: str
    mode: str
    query: str
    relevant_chunk_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CalibrationProfile:
    """One index tokenizer and query normalization combination."""

    profile_id: str
    query_profile: str
    text_tokenizer: dict[str, object]


@dataclass(frozen=True, slots=True)
class CalibrationConfig:
    """Frozen corpus, cases, candidates, and paired-test policy."""

    path: Path
    fingerprint: str
    schema: str
    corpus: tuple[CalibrationChunk, ...]
    queries: tuple[CalibrationCase, ...]
    profiles: tuple[CalibrationProfile, ...]
    baseline_profile: str
    candidate_profile: str
    k: int
    confidence: float
    resamples: int
    seed: int


@dataclass(frozen=True, slots=True)
class CaseReading:
    """One profile's held-out result for one query."""

    profile_id: str
    case_id: str
    category: str
    split: str
    hit_ids: tuple[str, ...]
    recall: float
    reciprocal_rank: float
    intact: float
    elapsed_ms: float

    def as_json_dict(self) -> dict[str, object]:
        """Return the canonical case-ledger row."""
        return {
            "case_id": self.case_id,
            "category": self.category,
            "elapsed_ms": self.elapsed_ms,
            "hit_ids": list(self.hit_ids),
            "intact": self.intact,
            "profile_id": self.profile_id,
            "recall": self.recall,
            "reciprocal_rank": self.reciprocal_rank,
            "split": self.split,
        }


@dataclass(frozen=True, slots=True)
class ProfileReading:
    """Aggregate quality and cost for one compared profile."""

    profile: CalibrationProfile
    tokenizer_fingerprint: str
    build_seconds: float
    index_bytes: int
    table_bytes: int
    p95_latency_ms: float
    metrics: RetrievalMetrics
    cases: tuple[CaseReading, ...]


@dataclass(frozen=True, slots=True)
class ComparisonReading:
    """One named candidate-minus-baseline paired comparison."""

    name: str
    candidate: str
    baseline: str
    paired: PairedComparison
    verdict: str


@dataclass(frozen=True, slots=True)
class CalibrationOutcome:
    """Published calibration identity and selected profile decision."""

    verdict: str
    selected_profile: str
    reindex_required: bool
    bundle_dir: Path
    manifest_fingerprint: str
    engine_version: str
    readings: tuple[ProfileReading, ...]
    comparisons: tuple[ComparisonReading, ...]

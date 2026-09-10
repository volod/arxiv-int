"""Typed inputs, readings, and decisions for the lexical second-opinion calibration."""

from dataclasses import dataclass
from pathlib import Path

from arxiv_int.evaluation.scoring.paired import PairedComparison

MODE_MATCH = "match"
MODE_IDENTIFIER = "identifier"
SPLIT_DEVELOPMENT = "development"
SPLIT_FINAL = "final"


@dataclass(frozen=True, slots=True)
class SplitChunk:
    """One judged, source-safe chunk with its offsets inside a synthetic document."""

    chunk_id: str
    document_id: str
    title: str
    body: str
    identifiers: str
    language: str
    start_char: int
    end_char: int


@dataclass(frozen=True, slots=True)
class SplitCase:
    """One frozen query with chunk-level relevance, hard-negative and forbidden judgments."""

    case_id: str
    cohort: str
    mode: str
    query: str
    relevant: tuple[str, ...]
    hard_negatives: tuple[str, ...]
    forbidden: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SplitData:
    """One checksum-verified split."""

    name: str
    fingerprint: str
    chunks: tuple[SplitChunk, ...]
    cases: tuple[SplitCase, ...]


@dataclass(frozen=True, slots=True)
class Arm:
    """One index profile served with one query profile."""

    index_profile: str
    query_profile: str

    @property
    def arm_id(self) -> str:
        """Return the stable ``index/query`` identity."""
        return f"{self.index_profile}/{self.query_profile}"


@dataclass(frozen=True, slots=True)
class Comparison:
    """One named candidate-minus-baseline arm comparison."""

    name: str
    candidate: str
    baseline: str


@dataclass(frozen=True, slots=True)
class DecisionPolicy:
    """Preregistered mandatory gates and paired-verdict thresholds."""

    identifier_exactness: float
    latency_p95_ms_max: float
    latency_p95_ratio_max: float
    latency_p95_increase_ms_max: float
    min_decided_pairs: int
    no_answer_false_positive_increase_max: int
    non_inferiority_margin: float
    syntax_new_errors_max: int
    syntax_forbidden_hits_max: int


@dataclass(frozen=True, slots=True)
class Protocol:
    """The frozen protocol plus the arms declaration that preregistration binds."""

    path: Path
    fingerprint: str
    arms_path: Path
    arms_fingerprint: str
    paradedb_version: str
    split_fingerprints: dict[str, str]
    cohorts: dict[str, tuple[str, ...]]
    decision: DecisionPolicy
    execution: dict[str, int]
    filler: dict[str, float]
    k_quality: int
    k_precision: int
    minimums: dict[str, int]
    confidence: float
    resamples: int
    primary_seed: int
    sensitivity_seeds: tuple[int, ...]
    index_profiles: dict[str, dict[str, object]]
    arms: tuple[Arm, ...]
    baseline: str
    candidate: str
    comparisons: tuple[Comparison, ...]


@dataclass(frozen=True, slots=True)
class CaseRun:
    """One arm's hits for one case, with every repeated latency sample."""

    arm_id: str
    case_id: str
    hits: tuple[str, ...]
    stage: str
    error: str
    latencies_ms: tuple[float, ...]
    stable: bool


@dataclass(frozen=True, slots=True)
class CaseScore:
    """Chunk-level quality and precision readings for one arm and case."""

    arm_id: str
    case_id: str
    cohort: str
    ndcg: float
    recall: float
    reciprocal_rank: float
    precision: float
    intact: float
    false_positive: bool
    hard_negatives: int
    forbidden_hits: int
    unjudged: int
    exact: bool


@dataclass(frozen=True, slots=True)
class BuildReading:
    """Repeated index build cost and final sizes for one index profile."""

    index_profile: str
    tokenizer_fingerprint: str
    build_seconds: tuple[float, ...]
    index_bytes: int
    table_bytes: int
    rows: int


@dataclass(frozen=True, slots=True)
class Endpoint:
    """One paired endpoint over one cohort group."""

    name: str
    metric: str
    candidate: str
    baseline: str
    items: int
    paired: PairedComparison
    verdict: str


@dataclass(frozen=True, slots=True)
class Decision:
    """Adopt, retain-baseline, or inconclusive with every gate and its evidence."""

    verdict: str
    reasons: tuple[str, ...]
    gates: dict[str, bool]
    quality: Endpoint
    precision: Endpoint
    seed_verdicts: dict[int, str]
    stable_hits: bool


@dataclass(frozen=True, slots=True)
class Execution:
    """Everything one split execution measured before publication."""

    split: SplitData
    engine_version: str
    filler_rows: int
    builds: tuple[BuildReading, ...]
    runs: tuple[CaseRun, ...]
    scores: tuple[CaseScore, ...]
    repetitions: dict[str, int]

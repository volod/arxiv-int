"""Typed policy, input, candidate, evidence, and output models for file classification."""

import hashlib
import json
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ClassifierWeights:
    """Relative contribution of text and validated metadata features."""

    text: float
    title: float
    path: float
    self_caption: float
    ancestor_caption: float


@dataclass(frozen=True, slots=True)
class EvaluationGates:
    """Predeclared acceptance limits for frozen held-out labels."""

    exact_accuracy: float
    hierarchical_f1: float
    mean_hierarchical_distance: float
    calibration_error: float
    exceptional_f1: float
    minimum_throughput_files_per_second: float
    maximum_peak_memory_mib: float


@dataclass(frozen=True, slots=True)
class ClassifierPolicy:
    """Versioned deterministic classifier operating profile."""

    profile_id: str
    profile_version: str
    algorithm_version: str
    batch_rows: int
    max_text_chars: int
    max_alternates: int
    minimum_matched_features: int
    primary_threshold: float
    margin_threshold: float
    alternate_threshold: float
    weights: ClassifierWeights
    gates: EvaluationGates
    sha256: str

    @property
    def classifier_id(self) -> str:
        """Bind the algorithm and complete profile content into one stable identity."""
        payload = f"{self.profile_id}:{self.profile_version}:{self.algorithm_version}:{self.sha256}"
        return hashlib.sha256(payload.encode("ascii")).hexdigest()


@dataclass(frozen=True, slots=True)
class DocumentText:
    """One checksum-validated normalized document available to a physical file."""

    document_id: str
    normalized_document_id: str
    title: str
    text: str


@dataclass(frozen=True, slots=True)
class PhysicalFile:
    """One physical inventory row plus direct/container-member normalized text."""

    occurrence_id: str
    silo_id: str
    relative_path: str
    content_hash: str | None
    status: str
    reason: str | None
    documents: tuple[DocumentText, ...]
    extraction_failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Candidate:
    """One taxonomy candidate and the decisive matched terms."""

    class_id: str
    score: float
    matched_terms: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Classification:
    """Complete mapping for one physical file."""

    primary: str
    alternates: tuple[str, ...]
    path: tuple[str, ...]
    confidence: float
    candidates: tuple[Candidate, ...]
    evidence: tuple[dict[str, object], ...]
    failure_reason: str | None
    document_ids: tuple[str, ...]


def classification_id(occurrence_id: str, scheme_id: str, classifier_id: str) -> str:
    """Derive an immutable row id from source, scheme, and classifier identities."""
    value = json.dumps([occurrence_id, scheme_id, classifier_id], ensure_ascii=True)
    return hashlib.sha256(value.encode("ascii")).hexdigest()

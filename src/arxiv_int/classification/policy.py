"""Load and validate the committed file-classifier operating profile."""

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.classification.model import ClassifierPolicy, ClassifierWeights, EvaluationGates
from arxiv_int.resources.paths import configs_root

CLASSIFIER_FILE = "classification/classifier.json"


def _mapping(value: Any, label: str) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def load_classifier_policy(project_root: Path | None = None) -> ClassifierPolicy:
    """Load the fingerprinted classifier policy from packaged or overlay configs."""
    path = configs_root(project_root) / CLASSIFIER_FILE
    payload = path.read_bytes()
    document = _mapping(json.loads(payload), "classifier profile")
    weights = _mapping(document.get("weights"), "weights")
    gates = _mapping(document.get("evaluationGates"), "evaluationGates")
    policy = ClassifierPolicy(
        profile_id=str(document.get("profileId") or ""),
        profile_version=str(document.get("profileVersion") or ""),
        algorithm_version=str(document.get("algorithmVersion") or ""),
        batch_rows=int(document.get("batchRows", 0)),
        max_text_chars=int(document.get("maxTextChars", 0)),
        max_alternates=int(document.get("maxAlternates", 0)),
        minimum_matched_features=int(document.get("minimumMatchedFeatures", 0)),
        primary_threshold=float(document.get("primaryThreshold", -1.0)),
        margin_threshold=float(document.get("marginThreshold", -1.0)),
        alternate_threshold=float(document.get("alternateThreshold", -1.0)),
        weights=ClassifierWeights(
            text=float(weights.get("text", 0.0)),
            title=float(weights.get("title", 0.0)),
            path=float(weights.get("path", 0.0)),
            self_caption=float(weights.get("selfCaption", 0.0)),
            ancestor_caption=float(weights.get("ancestorCaption", 0.0)),
        ),
        gates=EvaluationGates(
            exact_accuracy=float(gates.get("exactAccuracy", -1.0)),
            hierarchical_f1=float(gates.get("hierarchicalF1", -1.0)),
            mean_hierarchical_distance=float(gates.get("meanHierarchicalDistance", -1.0)),
            calibration_error=float(gates.get("calibrationError", -1.0)),
            exceptional_f1=float(gates.get("exceptionalF1", -1.0)),
            minimum_throughput_files_per_second=float(
                gates.get("minimumThroughputFilesPerSecond", -1.0)
            ),
            maximum_peak_memory_mib=float(gates.get("maximumPeakMemoryMiB", -1.0)),
        ),
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    _validate(policy)
    return policy


def _validate(policy: ClassifierPolicy) -> None:
    if not policy.profile_id or not policy.profile_version or not policy.algorithm_version:
        raise ValueError("classifier profile identities must be non-empty")
    if min(policy.batch_rows, policy.max_text_chars, policy.minimum_matched_features) < 1:
        raise ValueError("classifier batch, text, and matched-feature limits must be positive")
    if policy.max_alternates < 0:
        raise ValueError("classifier maxAlternates cannot be negative")
    thresholds = (
        policy.primary_threshold,
        policy.margin_threshold,
        policy.alternate_threshold,
    )
    if any(value < 0.0 or value > 1.0 for value in thresholds):
        raise ValueError("classifier thresholds must be in [0, 1]")
    weights = (
        policy.weights.text,
        policy.weights.title,
        policy.weights.path,
        policy.weights.self_caption,
        policy.weights.ancestor_caption,
    )
    if any(value <= 0.0 for value in weights):
        raise ValueError("classifier feature weights must be positive")

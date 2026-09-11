"""Load the frozen second-opinion protocol and its arms declaration."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.retrieval.query_normalization import load_query_policy
from arxiv_int.retrieval.second_opinion.model import Arm, Comparison, DecisionPolicy, Protocol
from arxiv_int.retrieval.second_opinion.splits import FrozenInputError, second_opinion_path

PROTOCOL_SCHEMA = "arxiv-int.retrieval.lexical-second-opinion-protocol.v1"
ARMS_SCHEMA = "arxiv-int.retrieval.lexical-second-opinion-arms.v1"
REQUIRED_COHORT_GROUPS = ("gate_identifier", "gate_syntax", "no_answer", "precision", "quality")


def load_protocol(project_root: Path | None = None) -> Protocol:
    """Load protocol.json and arms.json, then validate every cross-reference."""
    path = second_opinion_path(project_root, "protocol.json")
    arms_path = second_opinion_path(project_root, "arms.json")
    payload = _object(json.loads(path.read_text(encoding="ascii")), "protocol")
    declared = _object(json.loads(arms_path.read_text(encoding="ascii")), "arms")
    if payload.get("schema") != PROTOCOL_SCHEMA or declared.get("schema") != ARMS_SCHEMA:
        raise FrozenInputError("unsupported second-opinion protocol or arms schema")
    statistics = _object(payload["statistics"], "statistics")
    k = _object(payload["k"], "k")
    protocol = Protocol(
        path=path,
        fingerprint=hash_file(path)[0],
        arms_path=arms_path,
        arms_fingerprint=hash_file(arms_path)[0],
        paradedb_version=str(payload["paradedb_version"]),
        split_fingerprints={
            str(key): str(value) for key, value in _object(payload["splits"], "splits").items()
        },
        cohorts={
            str(key): tuple(str(item) for item in _list(value))
            for key, value in _object(payload["cohorts"], "cohorts").items()
        },
        decision=_decision(_object(payload["decision"], "decision")),
        execution=_integers(_object(payload["execution"], "execution")),
        filler={
            str(key): float(str(value))
            for key, value in _object(payload["filler"], "filler").items()
        },
        k_quality=int(str(k["quality"])),
        k_precision=int(str(k["precision"])),
        minimums=_integers(_object(payload["minimums"], "minimums")),
        confidence=float(str(statistics["confidence"])),
        resamples=int(str(statistics["resamples"])),
        primary_seed=int(str(statistics["primary_seed"])),
        sensitivity_seeds=tuple(int(str(item)) for item in _list(statistics["sensitivity_seeds"])),
        index_profiles={
            str(key): dict(_object(value, "index profile"))
            for key, value in _object(declared["index_profiles"], "index_profiles").items()
        },
        arms=tuple(_arm(item) for item in _list(declared["arms"])),
        baseline=str(declared["baseline"]),
        candidate=str(declared["candidate"]),
        comparisons=tuple(_comparison(item) for item in _list(declared["comparisons"])),
    )
    _validate(protocol)
    return protocol


def index_text_fields(tokenizer: Mapping[str, object]) -> dict[str, object]:
    """Return the complete ParadeDB text-fields declaration for one index profile."""
    analyzed = {"tokenizer": dict(tokenizer), "record": "position"}
    return {
        "body": analyzed,
        "document_id": {"tokenizer": {"type": "keyword"}, "fast": True},
        "identifiers": {
            "tokenizer": {"type": "whitespace", "lowercase": False},
            "record": "position",
        },
        "language": {"tokenizer": {"type": "keyword"}, "fast": True},
        "title": analyzed,
    }


def _validate(protocol: Protocol) -> None:
    missing = [name for name in REQUIRED_COHORT_GROUPS if name not in protocol.cohorts]
    if missing or set(protocol.split_fingerprints) != {"development", "final", "filler"}:
        raise FrozenInputError(f"protocol is missing cohort groups or split fingerprints {missing}")
    if not protocol.sensitivity_seeds or protocol.primary_seed not in protocol.sensitivity_seeds:
        raise FrozenInputError("the primary seed must be one of the sensitivity seeds")
    if min(protocol.k_quality, protocol.k_precision, protocol.resamples) <= 0:
        raise FrozenInputError("protocol k and resamples must be positive")
    _validate_arms(protocol)


def _validate_arms(protocol: Protocol) -> None:
    arm_ids = [arm.arm_id for arm in protocol.arms]
    if len(set(arm_ids)) != len(arm_ids):
        raise FrozenInputError("arms must be unique")
    query_profiles = set(load_query_policy().profiles)
    unknown = [
        arm.arm_id
        for arm in protocol.arms
        if arm.index_profile not in protocol.index_profiles
        or arm.query_profile not in query_profiles
    ]
    if unknown:
        raise FrozenInputError(f"arms name undeclared index or query profiles: {unknown}")
    referenced = {protocol.baseline, protocol.candidate}
    for item in protocol.comparisons:
        referenced |= {item.candidate, item.baseline}
    if referenced - set(arm_ids):
        raise FrozenInputError(
            f"comparisons name undeclared arms {sorted(referenced - set(arm_ids))}"
        )


def _decision(item: Mapping[str, object]) -> DecisionPolicy:
    return DecisionPolicy(
        identifier_exactness=float(str(item["identifier_exactness"])),
        latency_p95_ms_max=float(str(item["latency_p95_ms_max"])),
        latency_p95_ratio_max=float(str(item["latency_p95_ratio_max"])),
        latency_p95_increase_ms_max=float(str(item["latency_p95_increase_ms_max"])),
        min_decided_pairs=int(str(item["min_decided_pairs"])),
        no_answer_false_positive_increase_max=int(
            str(item["no_answer_false_positive_increase_max"])
        ),
        non_inferiority_margin=float(str(item["non_inferiority_margin"])),
        syntax_new_errors_max=int(str(item["syntax_new_errors_max"])),
        syntax_forbidden_hits_max=int(str(item["syntax_forbidden_hits_max"])),
    )


def _arm(value: object) -> Arm:
    item = _object(value, "arm")
    return Arm(str(item["index"]), str(item["query"]))


def _comparison(value: object) -> Comparison:
    item = _object(value, "comparison")
    return Comparison(str(item["name"]), str(item["candidate"]), str(item["baseline"]))


def _integers(item: Mapping[str, object]) -> dict[str, int]:
    return {str(key): int(str(value)) for key, value in item.items()}


def _object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise FrozenInputError(f"second-opinion {label} must be an object")
    return value


def _list(value: object) -> Sequence[object]:
    if not isinstance(value, list):
        raise FrozenInputError("second-opinion list field must be an array")
    return value

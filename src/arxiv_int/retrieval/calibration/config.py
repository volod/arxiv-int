"""Load and validate the frozen Russian BM25 calibration configuration."""

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.resources.paths import configs_root
from arxiv_int.retrieval.calibration.model import (
    CalibrationCase,
    CalibrationChunk,
    CalibrationConfig,
    CalibrationProfile,
)
from arxiv_int.retrieval.query_normalization import load_query_policy

CONFIG_NAME = "russian-bm25-calibration.json"
EXPECTED_SCHEMA = "arxiv-int.retrieval.lexical-calibration.v1"
REQUIRED_CATEGORIES = frozenset(
    {
        "abbreviation",
        "e_yo",
        "homoglyph",
        "identifier",
        "inflection",
        "keyboard_layout",
        "mixed_language",
        "ocr_noise",
        "transliteration",
    }
)


def load_calibration_config(project_root: Path | None = None) -> CalibrationConfig:
    """Load the packaged/overlaid fixture and enforce its frozen evaluation shape."""
    path = configs_root(project_root) / "retrieval" / CONFIG_NAME
    payload = _mapping(json.loads(path.read_text(encoding="ascii")), "configuration")
    corpus = tuple(_chunk(item) for item in _sequence(payload.get("corpus"), "corpus"))
    queries = tuple(_case(item) for item in _sequence(payload.get("queries"), "queries"))
    profiles = tuple(_profile(item) for item in _sequence(payload.get("profiles"), "profiles"))
    config = CalibrationConfig(
        path=path,
        fingerprint=hash_file(path)[0],
        schema=_text(payload, "schema"),
        corpus=corpus,
        queries=queries,
        profiles=profiles,
        baseline_profile=_text(payload, "baseline_profile"),
        candidate_profile=_text(payload, "candidate_profile"),
        k=_integer(payload, "k"),
        confidence=_number(payload, "confidence"),
        resamples=_integer(payload, "resamples"),
        seed=_integer(payload, "seed"),
    )
    _validate(config)
    return config


def profile_text_fields(profile: CalibrationProfile) -> dict[str, object]:
    """Return the complete ParadeDB text-fields declaration for one candidate."""
    analyzed = {"tokenizer": profile.text_tokenizer, "record": "position"}
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


def _chunk(value: object) -> CalibrationChunk:
    item = _mapping(value, "corpus item")
    return CalibrationChunk(
        *(_text(item, field) for field in CalibrationChunk.__dataclass_fields__)
    )


def _case(value: object) -> CalibrationCase:
    item = _mapping(value, "query item")
    relevant = tuple(str(entry) for entry in _sequence(item.get("relevant_chunk_ids"), "relevant"))
    return CalibrationCase(
        case_id=_text(item, "id"),
        category=_text(item, "category"),
        split=_text(item, "split"),
        mode=_text(item, "mode"),
        query=_text(item, "query"),
        relevant_chunk_ids=relevant,
    )


def _profile(value: object) -> CalibrationProfile:
    item = _mapping(value, "profile")
    tokenizer = dict(_mapping(item.get("text_tokenizer"), "text_tokenizer"))
    return CalibrationProfile(_text(item, "id"), _text(item, "query_profile"), tokenizer)


def _validate(config: CalibrationConfig) -> None:
    if config.schema != EXPECTED_SCHEMA:
        raise ValueError(f"unsupported calibration schema {config.schema!r}")
    if config.k <= 0 or config.resamples <= 0 or not 0.0 < config.confidence < 1.0:
        raise ValueError("calibration metric parameters are invalid")
    _validate_identities(config)
    _validate_queries(config)


def _validate_identities(config: CalibrationConfig) -> None:
    chunk_ids = [item.chunk_id for item in config.corpus]
    case_ids = [item.case_id for item in config.queries]
    profile_ids = [item.profile_id for item in config.profiles]
    _unique(chunk_ids, "chunk")
    _unique(case_ids, "query")
    _unique(profile_ids, "profile")
    known_query_profiles = set(load_query_policy().profiles)
    if {config.baseline_profile, config.candidate_profile} - set(profile_ids):
        raise ValueError("baseline or candidate profile is not declared")
    if any(item.query_profile not in known_query_profiles for item in config.profiles):
        raise ValueError("calibration profile names an unknown query policy")


def _validate_queries(config: CalibrationConfig) -> None:
    known_chunks = {item.chunk_id for item in config.corpus}
    if any(item.mode not in {"match", "identifier"} for item in config.queries):
        raise ValueError("calibration query mode must be match or identifier")
    if any(item.split != "final" for item in config.queries):
        raise ValueError("calibration bundle may score only the frozen final split")
    if any(not item.relevant_chunk_ids for item in config.queries):
        raise ValueError("every calibration query needs relevant chunks")
    if any(set(item.relevant_chunk_ids) - known_chunks for item in config.queries):
        raise ValueError("calibration query references an unknown chunk")
    categories = {item.category for item in config.queries}
    if not categories >= REQUIRED_CATEGORIES:
        raise ValueError("calibration final split does not cover every required category")


def _unique(values: list[str], label: str) -> None:
    if not values or len(values) != len(set(values)):
        raise ValueError(f"calibration {label} identities are empty or duplicated")


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"calibration {label} must be an object")
    return value


def _sequence(value: object, label: str) -> Sequence[object]:
    if not isinstance(value, list):
        raise ValueError(f"calibration {label} must be an array")
    return value


def _text(item: Mapping[str, object], field: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"calibration field {field} must be non-empty text")
    return value


def _integer(item: Mapping[str, object], field: str) -> int:
    value = item.get(field)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"calibration field {field} must be an integer")
    return value


def _number(item: Mapping[str, object], field: str) -> float:
    value = item.get(field)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"calibration field {field} must be numeric")
    return float(value)

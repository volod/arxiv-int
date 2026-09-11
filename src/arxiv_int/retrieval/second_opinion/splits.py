"""Load checksum-frozen development/final splits and the filler vocabulary."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.resources.paths import configs_root
from arxiv_int.retrieval.second_opinion.model import (
    MODE_IDENTIFIER,
    MODE_MATCH,
    SPLIT_FINAL,
    Protocol,
    SplitCase,
    SplitChunk,
    SplitData,
)

SECOND_OPINION_DIR = ("retrieval", "second-opinion")
SPLIT_SCHEMA = "arxiv-int.retrieval.lexical-second-opinion-split.v1"
FILLER_SCHEMA = "arxiv-int.retrieval.lexical-second-opinion-filler.v1"


class FrozenInputError(ValueError):
    """Raised when a frozen second-opinion input no longer matches its fingerprint."""


@dataclass(frozen=True, slots=True)
class FillerVocabulary:
    """Collision-audited everyday vocabulary and stopwords for the scale corpus."""

    fingerprint: str
    vocabulary: tuple[str, ...]
    stopwords: tuple[str, ...]


def second_opinion_path(project_root: Path | None, name: str) -> Path:
    """Return one packaged/overlaid second-opinion input file."""
    return configs_root(project_root).joinpath(*SECOND_OPINION_DIR, name)


def verified_payload(path: Path, expected: str, label: str) -> tuple[dict[str, object], str]:
    """Read one frozen JSON file after checking its SHA-256 against the protocol."""
    fingerprint = hash_file(path)[0]
    if fingerprint != expected:
        raise FrozenInputError(
            f"frozen {label} input changed: expected {expected}, found {fingerprint}"
        )
    payload = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(payload, dict):
        raise FrozenInputError(f"frozen {label} input must be a JSON object")
    return payload, fingerprint


def load_split(project_root: Path | None, protocol: Protocol, name: str) -> SplitData:
    """Load and validate one frozen split."""
    path = second_opinion_path(project_root, f"{name}.json")
    payload, fingerprint = verified_payload(path, protocol.split_fingerprints[name], name)
    if payload.get("schema") != SPLIT_SCHEMA or payload.get("split") != name:
        raise FrozenInputError(f"{name} split has an unexpected schema or split name")
    chunks = tuple(_chunk(item) for item in _items(payload, "chunks"))
    cases = tuple(_case(item) for item in _items(payload, "cases"))
    split = SplitData(name, fingerprint, chunks, cases)
    _validate(split, protocol)
    return split


def load_filler(project_root: Path | None, protocol: Protocol) -> FillerVocabulary:
    """Load the frozen filler vocabulary."""
    path = second_opinion_path(project_root, "filler.json")
    payload, fingerprint = verified_payload(path, protocol.split_fingerprints["filler"], "filler")
    if payload.get("schema") != FILLER_SCHEMA:
        raise FrozenInputError("filler vocabulary has an unexpected schema")
    vocabulary = tuple(str(item) for item in _items(payload, "vocabulary"))
    stopwords = tuple(str(item) for item in _items(payload, "stopwords"))
    if not vocabulary or not stopwords or set(vocabulary) & set(stopwords):
        raise FrozenInputError("filler vocabulary and stopwords must be non-empty and disjoint")
    return FillerVocabulary(fingerprint, vocabulary, stopwords)


def require_distinct(development: SplitData, final: SplitData) -> None:
    """Refuse shared case ids, chunk ids, or query texts between the two splits."""
    shared_cases = {item.case_id for item in development.cases} & {i.case_id for i in final.cases}
    shared_chunks = {i.chunk_id for i in development.chunks} & {i.chunk_id for i in final.chunks}
    shared_queries = {i.query for i in development.cases} & {i.query for i in final.cases}
    if shared_cases or shared_chunks or shared_queries:
        raise FrozenInputError("development and final splits must not share cases or queries")


def require_minimums(protocol: Protocol, split: SplitData) -> None:
    """Refuse a final split below the preregistered cohort sizes."""
    counts = {
        "quality_cases": _count(split, protocol.cohorts["quality"], MODE_MATCH),
        "precision_cases": _count(split, protocol.cohorts["precision"], MODE_MATCH),
        "no_answer_cases": _count(split, protocol.cohorts["no_answer"], MODE_MATCH),
        "identifier_checks": _count(split, protocol.cohorts["gate_identifier"], MODE_IDENTIFIER),
        "syntax_probes": _count(split, protocol.cohorts["gate_syntax"], MODE_MATCH),
    }
    short = {name: count for name, count in counts.items() if count < protocol.minimums[name]}
    if short:
        raise FrozenInputError(f"{split.name} split is below preregistered minimums: {short}")


def _count(split: SplitData, cohorts: Sequence[str], mode: str) -> int:
    return sum(1 for case in split.cases if case.cohort in cohorts and case.mode == mode)


def _validate(split: SplitData, protocol: Protocol) -> None:
    chunk_ids = [item.chunk_id for item in split.chunks]
    case_ids = [item.case_id for item in split.cases]
    if len(set(chunk_ids)) != len(chunk_ids) or len(set(case_ids)) != len(case_ids):
        raise FrozenInputError(f"{split.name} split has duplicate identities")
    known = set(chunk_ids)
    cohorts = {name for group in protocol.cohorts.values() for name in group}
    identifier = set(protocol.cohorts["gate_identifier"])
    for case in split.cases:
        judged = (*case.relevant, *case.hard_negatives, *case.forbidden)
        if set(judged) - known:
            raise FrozenInputError(f"case {case.case_id} references an unknown chunk")
        if case.cohort not in cohorts:
            raise FrozenInputError(f"case {case.case_id} names an undeclared cohort")
        if (case.mode == MODE_IDENTIFIER) != (case.cohort in identifier):
            raise FrozenInputError(f"case {case.case_id} mode does not match its cohort")
    if split.name == SPLIT_FINAL:
        require_minimums(protocol, split)


def _chunk(value: object) -> SplitChunk:
    item = _mapping(value)
    return SplitChunk(
        chunk_id=str(item["chunk_id"]),
        document_id=str(item["document_id"]),
        title=str(item["title"]),
        body=str(item["body"]),
        identifiers=str(item["identifiers"]),
        language=str(item["language"]),
        start_char=int(str(item["start_char"])),
        end_char=int(str(item["end_char"])),
    )


def _case(value: object) -> SplitCase:
    item = _mapping(value)
    mode = str(item["mode"])
    if mode not in {MODE_MATCH, MODE_IDENTIFIER}:
        raise FrozenInputError(f"unknown case mode {mode!r}")
    return SplitCase(
        case_id=str(item["id"]),
        cohort=str(item["cohort"]),
        mode=mode,
        query=str(item["query"]),
        relevant=_ids(item, "relevant_chunk_ids"),
        hard_negatives=_ids(item, "hard_negative_chunk_ids"),
        forbidden=_ids(item, "forbidden_chunk_ids"),
    )


def _ids(item: Mapping[str, object], field: str) -> tuple[str, ...]:
    return tuple(str(entry) for entry in _items(item, field))


def _items(item: Mapping[str, object], field: str) -> Sequence[object]:
    value = item.get(field)
    if not isinstance(value, list):
        raise FrozenInputError(f"second-opinion field {field} must be an array")
    return value


def _mapping(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise FrozenInputError("second-opinion items must be objects")
    return value

"""Record filename sequence, group abbrev, and task-id parsing."""

import re
from dataclasses import dataclass
from pathlib import Path

# Capability id -> short group token used in record filenames.
# Keep abbrevs unique; longer tokens are matched before shorter ones when parsing.
GROUP_ABBREVIATIONS: dict[str, str] = {
    "project-foundation": "foundation",
    "portable-runtime": "runtime",
    "contract-governance": "contract-gov",
    "canonical-store": "store",
    "local-inference": "inference",
    "evaluation-foundation": "eval-found",
    "pipeline-control": "pipeline",
    "corpus-foundation": "corpus",
    "lexical-retrieval": "lexical",
    "archive-classification": "archive-cls",
    "russian-nlp": "rus-nlp",
    "identity-ontology-graph": "identity",
    "knowledge-extraction": "knowledge",
    "concept-graph": "concept",
    "graph-analytics": "graph-an",
    "domain-investigation-artifacts": "domain",
    "anomaly-analysis": "anomaly",
    "discovery-visualization": "discovery",
    "evaluation-evidence": "eval-evid",
    "operational-recovery": "ops",
    "semantic-retrieval": "semantic",
    "graph-constrained-agents": "agents",
    "archive-organization": "archive-org",
    # Cross-cutting governance / instruction / audit work.
    "governance": "govern",
    # Fixture capability used by plan-integrity unit tests.
    "feature": "feature",
}

KNOWN_GROUP_ABBREVS: frozenset[str] = frozenset(GROUP_ABBREVIATIONS.values())
_GROUP_BY_LENGTH = tuple(sorted(KNOWN_GROUP_ABBREVS, key=len, reverse=True))
_SEQUENCE_PREFIX = re.compile(r"^(?P<seq>\d{4})-(?P<rest>.+)$")


@dataclass(frozen=True, slots=True)
class RecordFilename:
    """Parsed ``NNNN-group-task-id`` record file stem."""

    sequence: int
    group: str
    task_id: str

    @property
    def stem(self) -> str:
        return f"{self.sequence:04d}-{self.group}-{self.task_id}"


def group_abbrev_for(capability_id: str) -> str:
    """Return the filename group token for a capability id."""
    try:
        return GROUP_ABBREVIATIONS[capability_id]
    except KeyError as error:
        raise KeyError(
            f"no record group abbrev for capability `{capability_id}`; "
            "add it to GROUP_ABBREVIATIONS"
        ) from error


def parse_record_stem(stem: str) -> RecordFilename | None:
    """Parse a sequenced record stem, or return None for a bare task-id stem."""
    matched = _SEQUENCE_PREFIX.match(stem)
    if matched is None:
        return None
    rest = matched.group("rest")
    for group in _GROUP_BY_LENGTH:
        prefix = f"{group}-"
        if rest.startswith(prefix) and rest[len(prefix) :]:
            return RecordFilename(
                sequence=int(matched.group("seq")),
                group=group,
                task_id=rest[len(prefix) :],
            )
    return None


def record_identifier_from_stem(stem: str) -> str:
    """Return the stable task id encoded in a record file stem or link target."""
    parsed = parse_record_stem(stem)
    return parsed.task_id if parsed is not None else stem


def next_record_sequence(records_dir: Path) -> int:
    """Return the next unused 4-digit sequence for a new record file."""
    highest = 0
    if records_dir.is_dir():
        for path in records_dir.glob("*.md"):
            parsed = parse_record_stem(path.stem)
            if parsed is not None:
                highest = max(highest, parsed.sequence)
    return highest + 1


def build_record_filename(sequence: int, capability_id: str, task_id: str) -> str:
    """Return ``NNNN-group-task-id.md`` for a new durable task record."""
    if sequence < 1 or sequence > 9999:
        raise ValueError(f"record sequence out of range: {sequence}")
    if not task_id or task_id.startswith("-") or task_id.endswith("-"):
        raise ValueError(f"invalid task id for record filename: {task_id!r}")
    group = group_abbrev_for(capability_id)
    return f"{sequence:04d}-{group}-{task_id}.md"

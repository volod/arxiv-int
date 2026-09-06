"""Read durable task records so plan references can be resolved against real evidence."""

import re
from dataclasses import dataclass, field
from pathlib import Path

from arxiv_int.quality.plan_model import Task, fenced_blocks, parse_task_block, unfenced_lines
from arxiv_int.quality.record_naming import (
    KNOWN_GROUP_ABBREVS,
    parse_record_stem,
    record_identifier_from_stem,
)

RECORDS_DIR = Path("docs/impl/records")
INDEX_NAME = "README.md"
TEMPLATE_NAME = "template.md"
SNAPSHOT_LANGUAGE = "markdown"
ACCEPTED_STATE = "accepted"
UNAVAILABLE_MARKER = "unavailable"

NOTE_ID = re.compile(r"\bAUD-[a-z0-9][a-z0-9-]*\b")
_LINK_TARGET = re.compile(r"\]\((?P<target>[^)\s]+)\)")
_IDENTIFIER = re.compile(r"- (?:Task id|Id)[^:]*:\s*`(?P<id>[a-z0-9][a-z0-9-]*)`")
_STATE = re.compile(r"^- State:\s*(?P<state>.+?)\s*$", re.MULTILINE)
_HEADING = re.compile(r"^##+\s+(?P<title>.+?)\s*$")
_TABLE_ROW = re.compile(r"^\|")
_TABLE_RULE = re.compile(r"^\|[\s|:-]+\|\s*$")
_BLOCKING = re.compile(r"(?<!non)(?<!non-)\bblocking\b", re.IGNORECASE)
_RESOLVED = re.compile(r"\bresolved\b", re.IGNORECASE)
_EVIDENCE_SECTION = re.compile(r"evidence|verification", re.IGNORECASE)
_HANDOFF_SECTION = re.compile(r"handoff|audit", re.IGNORECASE)
_NO_NOTES = re.compile(r"none identified", re.IGNORECASE)
_REFACTOR_VERDICT = re.compile(r"\b(no[ -]refactor|refactor needed|no refactoring needed)\b", re.I)
_PROCEED_VERDICT = re.compile(r"\b(proceed|blocked)\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class AuditNote:
    """One routed audit observation carried by a record."""

    identifier: str
    blocking: bool
    resolved: bool
    owners: tuple[str, ...]


@dataclass(slots=True)
class Record:
    """One durable task record and the evidence it carries."""

    identifier: str
    path: Path
    state: str = ""
    snapshot: Task | None = None
    snapshot_unavailable: bool = False
    evidence_rows: int = 0
    notes: tuple[AuditNote, ...] = ()
    declares_no_notes: bool = False
    refactor_verdict: bool = False
    proceed_verdict: bool = False
    sections: tuple[str, ...] = field(default=())

    @property
    def accepted(self) -> bool:
        """Return whether the record declares an accepted task."""
        return self.state.strip().lower().startswith(ACCEPTED_STATE)


def _section_of(title: str) -> str:
    if _EVIDENCE_SECTION.search(title):
        return "evidence"
    return "handoff" if _HANDOFF_SECTION.search(title) else "other"


def _table_rows(lines: list[str]) -> int:
    rows = [line for line in lines if _TABLE_ROW.match(line)]
    rules = sum(1 for line in rows if _TABLE_RULE.match(line))
    return max(len(rows) - 2 * rules, 0)


def _declaration(line: str) -> str | None:
    """Return the leading cell of a table row or bullet that may declare a note."""
    if line.startswith("|"):
        cells = [cell for cell in line.split("|") if cell.strip()]
        return cells[0] if cells else None
    return line[2:] if line.startswith("- ") else None


def _note(row: str) -> AuditNote | None:
    declaration = _declaration(row)
    identifier = NOTE_ID.search(declaration) if declaration else None
    if identifier is None:
        return None
    return AuditNote(
        identifier=identifier.group(0),
        blocking=bool(_BLOCKING.search(row)),
        resolved=bool(_RESOLVED.search(row)),
        owners=tuple(_LINK_TARGET.findall(row)),
    )


def _grouped_lines(text: str) -> tuple[dict[str, list[str]], tuple[str, ...]]:
    grouped: dict[str, list[str]] = {"evidence": [], "handoff": [], "other": []}
    titles: list[str] = []
    current = "other"
    for line in unfenced_lines(text):
        heading = _HEADING.match(line)
        if heading:
            titles.append(heading.group("title"))
            current = _section_of(heading.group("title"))
            continue
        grouped[current].append(line)
    return grouped, tuple(titles)


def _snapshot(text: str) -> tuple[Task | None, bool]:
    for block in fenced_blocks(text, SNAPSHOT_LANGUAGE):
        task = parse_task_block(block)
        if task is not None:
            return task, False
    unavailable = any(
        UNAVAILABLE_MARKER in line.lower() and "task" in line.lower()
        for line in unfenced_lines(text)
    )
    return None, unavailable


def read_record(path: Path) -> Record:
    """Read one record file into its resolvable identity, evidence, and notes."""
    text = path.read_text(encoding="utf-8")
    grouped, titles = _grouped_lines(text)
    identifier = _IDENTIFIER.search(text)
    state = _STATE.search(text)
    snapshot, unavailable = _snapshot(text)
    handoff = grouped["handoff"]
    notes = [note for note in (_note(line) for line in handoff) if note is not None]
    handoff_text = "\n".join(handoff)
    parsed = parse_record_stem(path.stem)
    fallback_id = parsed.task_id if parsed is not None else path.stem
    return Record(
        identifier=identifier.group("id") if identifier else fallback_id,
        path=path,
        state=state.group("state") if state else "",
        snapshot=snapshot,
        snapshot_unavailable=unavailable,
        evidence_rows=_table_rows(grouped["evidence"]),
        notes=tuple(notes),
        declares_no_notes=bool(_NO_NOTES.search(handoff_text)),
        refactor_verdict=bool(_REFACTOR_VERDICT.search(text)),
        proceed_verdict=bool(_PROCEED_VERDICT.search(handoff_text)),
        sections=titles,
    )


def read_records(project_root: Path) -> dict[str, Record]:
    """Read every durable record, keyed by stable task id, excluding index and template."""
    directory = project_root / RECORDS_DIR
    if not directory.is_dir():
        return {}
    records: dict[str, Record] = {}
    for path in sorted(directory.glob("*.md")):
        if path.name in (INDEX_NAME, TEMPLATE_NAME):
            continue
        record = read_record(path)
        records.setdefault(record.identifier, record)
    return records


def indexed_records(project_root: Path) -> set[str]:
    """Return the task ids linked from the record index."""
    index = project_root / RECORDS_DIR / INDEX_NAME
    if not index.is_file():
        return set()
    targets = _LINK_TARGET.findall(index.read_text(encoding="utf-8"))
    return {record_identifier_from_stem(Path(target.partition("#")[0]).stem) for target in targets}


def _filename_findings(record: Record, where: str) -> list[str]:
    findings: list[str] = []
    parsed = parse_record_stem(record.path.stem)
    if parsed is None:
        if record.path.stem != record.identifier:
            findings.append(
                f"{where}: declares id `{record.identifier}` but is filed as `{record.path.stem}`"
            )
        return findings
    if parsed.task_id != record.identifier:
        findings.append(
            f"{where}: declares id `{record.identifier}` but filename task id is `{parsed.task_id}`"
        )
    if parsed.group not in KNOWN_GROUP_ABBREVS:
        findings.append(f"{where}: uses unknown group abbrev `{parsed.group}`")
    return findings


def _accepted_findings(record: Record, where: str) -> list[str]:
    findings: list[str] = []
    if record.snapshot is None and not record.snapshot_unavailable:
        findings.append(f"{where}: accepted record keeps no fenced accepted-task snapshot")
    if record.snapshot is not None and record.snapshot.identifier != record.identifier:
        findings.append(
            f"{where}: snapshot task `{record.snapshot.identifier}` does not match the record id"
        )
    if record.evidence_rows == 0:
        findings.append(f"{where}: accepted record carries no acceptance evidence row")
    if not record.notes and not record.declares_no_notes:
        findings.append(f"{where}: accepted record declares no audit handoff result")
    checkpoint = record.snapshot is not None and record.snapshot.is_checkpoint
    if checkpoint and not (record.refactor_verdict and record.proceed_verdict):
        findings.append(f"{where}: accepted checkpoint states no refactor and proceed verdict")
    return findings


def _scan_record_files(directory: Path) -> tuple[list[Record], list[str]]:
    findings: list[str] = []
    seen_sequences: dict[int, str] = {}
    by_id: dict[str, list[Path]] = {}
    loaded: list[Record] = []
    for path in sorted(directory.glob("*.md")):
        if path.name in (INDEX_NAME, TEMPLATE_NAME):
            continue
        record = read_record(path)
        loaded.append(record)
        by_id.setdefault(record.identifier, []).append(path)
        parsed = parse_record_stem(path.stem)
        if parsed is None:
            continue
        prior = seen_sequences.get(parsed.sequence)
        if prior is not None:
            findings.append(
                f"{RECORDS_DIR / path.name}: reuses sequence {parsed.sequence:04d} "
                f"already used by `{prior}`"
            )
        else:
            seen_sequences[parsed.sequence] = path.name
    for identifier, paths in sorted(by_id.items()):
        if len(paths) > 1:
            names = ", ".join(path.name for path in paths)
            findings.append(f"{RECORDS_DIR}: duplicate record id `{identifier}` in {names}")
    return loaded, findings


def _record_body_findings(record: Record, indexed: set[str]) -> list[str]:
    where = f"{RECORDS_DIR / record.path.name}"
    findings = _filename_findings(record, where)
    if not record.state:
        findings.append(f"{where}: declares no `State`")
    if record.identifier not in indexed:
        findings.append(f"{where}: is not linked from the record index")
    findings.extend(
        f"{where}: audit note `{note.identifier}` names no owner"
        for note in record.notes
        if not note.owners
    )
    if record.accepted:
        findings.extend(_accepted_findings(record, where))
    return findings


def record_findings(project_root: Path) -> list[str]:
    """Return every record that cannot stand in for the task text it replaced."""
    if not (project_root / RECORDS_DIR).is_dir():
        return [f"missing required directory: {RECORDS_DIR}"]
    loaded, findings = _scan_record_files(project_root / RECORDS_DIR)
    indexed = indexed_records(project_root)
    for record in loaded:
        findings.extend(_record_body_findings(record, indexed))
    return findings

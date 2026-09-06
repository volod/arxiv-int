"""Resolve plan prerequisites, checkpoints, and audit notes against records."""

import re
from dataclasses import dataclass

from arxiv_int.quality.plan_model import Task
from arxiv_int.quality.plan_records import NOTE_ID, Record

TASK_REFERENCE = "task"
RECORD_REFERENCE = "record"
NO_CHECKPOINT = "none"

_TASK_TOKEN = re.compile(r"`(?P<id>[a-z0-9][a-z0-9-]*-[a-z0-9-]*)`")
_MARKDOWN_LINK = re.compile(r"\[(?P<label>[^\]]*)\]\((?P<target>[^)\s]+)\)")
_RECORD_TARGET = re.compile(r"^(?:\.\./)*records/(?P<stem>[a-z0-9][a-z0-9-]*)\.md(?:#[a-z0-9-]*)?$")
_CLAUSE = re.compile(r";|\n|(?<=\.)\s")
_CONDITIONAL = re.compile(
    r"\b(if|when|unless|only|optional|conditional|conditionally|otherwise|depending)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Reference:
    """One prerequisite named by a task, and whether a branch selects it."""

    identifier: str
    kind: str
    conditional: bool


def _record_stem(target: str) -> str | None:
    matched = _RECORD_TARGET.match(target)
    return matched.group("stem") if matched else None


def dependency_references(value: str) -> list[Reference]:
    """Return every prerequisite named in a dependency field, clause by clause."""
    references: list[Reference] = []
    for clause in _CLAUSE.split(value):
        if not clause or not clause.strip():
            continue
        conditional = bool(_CONDITIONAL.search(clause))
        references.extend(
            Reference(matched.group("id"), TASK_REFERENCE, conditional)
            for matched in _TASK_TOKEN.finditer(clause)
        )
        for link in _MARKDOWN_LINK.finditer(clause):
            stem = _record_stem(link.group("target"))
            if stem:
                references.append(Reference(stem, RECORD_REFERENCE, conditional))
    return references


def task_references(task: Task) -> list[Reference]:
    """Return the prerequisites declared by one task."""
    return dependency_references(task.fields.get("dependencies", ""))


def audit_claims(task: Task) -> list[tuple[str, str]]:
    """Return the (record, note) pairs a task claims as audit inputs."""
    claims: list[tuple[str, str]] = []
    for link in _MARKDOWN_LINK.finditer(task.fields.get("audit inputs", "")):
        stem = _record_stem(link.group("target"))
        if stem:
            claims.extend((stem, note) for note in NOTE_ID.findall(link.group("label")))
    return claims


def blocking_prerequisites(task: Task, open_tasks: set[str]) -> tuple[str, ...]:
    """Return the unconditional open tasks that must finish before this one starts."""
    blocking = {
        reference.identifier
        for reference in task_references(task)
        if reference.kind == TASK_REFERENCE
        and not reference.conditional
        and reference.identifier in open_tasks
        and reference.identifier != task.identifier
    }
    return tuple(sorted(blocking))


def _reference_failure(
    reference: Reference,
    identifier: str,
    open_tasks: set[str],
    records: dict[str, Record],
) -> str | None:
    if reference.identifier == identifier:
        return "depends on itself"
    record = records.get(reference.identifier)
    if reference.kind == RECORD_REFERENCE:
        if record is None:
            return f"depends on missing record `{reference.identifier}`"
        return None if record.accepted else f"depends on unaccepted record `{reference.identifier}`"
    if reference.identifier in open_tasks:
        return None
    if record is None:
        return f"depends on unknown task `{reference.identifier}`"
    return None if record.accepted else f"depends on unaccepted record `{reference.identifier}`"


def _cycles(edges: dict[str, tuple[str, ...]]) -> list[tuple[str, ...]]:
    found: dict[frozenset[str], tuple[str, ...]] = {}
    visited: set[str] = set()

    def walk(node: str, path: list[str]) -> None:
        if node in path:
            cycle = tuple(path[path.index(node) :])
            found.setdefault(frozenset(cycle), cycle)
            return
        if node in visited:
            return
        visited.add(node)
        for successor in edges.get(node, ()):
            walk(successor, [*path, node])

    for start in edges:
        walk(start, [])
    return [found[key] for key in sorted(found, key=lambda item: sorted(item))]


def dependency_findings(
    plan_doc: str,
    tasks: list[Task],
    records: dict[str, Record],
) -> list[str]:
    """Return every prerequisite that does not resolve, plus required-ordering cycles."""
    findings: list[str] = []
    open_tasks = {task.identifier for task in tasks}
    edges: dict[str, tuple[str, ...]] = {}
    for task in tasks:
        where = f"{plan_doc}: `{task.identifier}`"
        for reference in task_references(task):
            failure = _reference_failure(reference, task.identifier, open_tasks, records)
            if failure:
                findings.append(f"{where}: {failure}")
        edges[task.identifier] = blocking_prerequisites(task, open_tasks)
    findings.extend(
        f"{plan_doc}: dependency cycle {' -> '.join([*cycle, cycle[0]])}"
        for cycle in _cycles(edges)
    )
    return findings


def _checkpoint_failures(task: Task, known: set[str]) -> list[str]:
    value = task.fields.get("review checkpoint", "")
    if not value:
        return ["missing non-empty `Review Checkpoint` field"]
    if value.strip().lower().startswith(NO_CHECKPOINT):
        return []
    named = [matched.group("id") for matched in _TASK_TOKEN.finditer(value)]
    if not named:
        return ["review checkpoint names no checkpoint id"]
    return [
        f"review checkpoint `{identifier}` is not a known checkpoint"
        for identifier in named
        if identifier not in known
    ]


def checkpoint_findings(plan_doc: str, tasks: list[Task], records: dict[str, Record]) -> list[str]:
    """Return every review checkpoint that names no resolvable owner."""
    known = {task.identifier for task in tasks if task.is_checkpoint}
    known.update(
        identifier
        for identifier, record in records.items()
        if record.accepted and record.snapshot is not None and record.snapshot.is_checkpoint
    )
    return [
        f"{plan_doc}: `{task.identifier}`: {failure}"
        for task in tasks
        for failure in _checkpoint_failures(task, known)
    ]


def _claim_findings(
    plan_doc: str,
    task: Task,
    records: dict[str, Record],
) -> list[str]:
    findings: list[str] = []
    for stem, claim in audit_claims(task):
        record = records.get(stem)
        if record is None:
            findings.append(
                f"{plan_doc}: `{task.identifier}`: audit input names unknown record `{stem}`"
            )
        elif claim not in {declared.identifier for declared in record.notes}:
            findings.append(
                f"{plan_doc}: `{task.identifier}`: audit input `{claim}` is not declared in `{stem}`"
            )
    return findings


def note_findings(plan_doc: str, tasks: list[Task], records: dict[str, Record]) -> list[str]:
    """Return audit notes that no task claims and claims that name no declared note."""
    claimed = {claim for task in tasks for claim in audit_claims(task)}
    findings = [finding for task in tasks for finding in _claim_findings(plan_doc, task, records)]
    findings.extend(
        f"{record.path.name}: audit note `{note.identifier}` has no owner"
        for identifier, record in sorted(records.items())
        for note in record.notes
        if not note.resolved and (identifier, note.identifier) not in claimed
    )
    return findings

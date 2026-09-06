"""Parsers for the capability registry and forward implementation plan."""

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

REGISTRY_HEADING = "## Capability Registry"
AGENT_SECTION = "Agent Implementation Tasks"
HUMAN_SECTION = "Human-Assisted Tasks"
PLAN_SECTIONS = (AGENT_SECTION, HUMAN_SECTION)
CHECKPOINT_KIND = "checkpoint"

_ROW = re.compile(r"^\|(?P<cells>.+)\|\s*$")
_CAPABILITY = re.compile(r"^`(?P<id>[a-z0-9-]+)`$")
_SECTION = re.compile(r"^## (?!#)(?P<title>.+?)\s*$")
_GROUP = re.compile(r"^### .+ -- `(?P<id>[a-z0-9-]+)`\s*$")
_TASK = re.compile(r"^#### (?P<id>[a-z0-9][a-z0-9-]*)(?P<optional> \(optional\))?\s*$")
_FIELD = re.compile(r"^- (?P<key>[A-Za-z][A-Za-z -]+):\s*(?P<value>.*)$")
_SERVES = re.compile(r"^`(?P<id>[a-z0-9-]+)`(?:\s|$)")
_FENCE = "```"


@dataclass(frozen=True, slots=True)
class Capability:
    """One product capability and its delivery contract."""

    identifier: str
    status: str
    evaluation: str
    implementation: str


@dataclass(slots=True)
class Task:
    """One forward task and the metadata used to schedule it."""

    identifier: str
    section: str
    group: str
    optional: bool
    fields: dict[str, str] = field(default_factory=dict)
    repeated_fields: tuple[str, ...] = ()

    @property
    def serves(self) -> str | None:
        """Return the capability id declared by the task."""
        value = self.fields.get("serves", "")
        matched = _SERVES.match(value)
        return matched.group("id") if matched else None

    @property
    def agent_status(self) -> str | None:
        """Return the normalized execution status when present."""
        value = self.fields.get("agent status")
        return value.strip().upper() if value else None

    @property
    def is_checkpoint(self) -> bool:
        """Return whether the task is a bounded review checkpoint."""
        return self.fields.get("task kind", "").strip().lower() == CHECKPOINT_KIND


def _cells(line: str) -> list[str] | None:
    matched = _ROW.match(line.strip())
    return [cell.strip() for cell in matched.group("cells").split("|")] if matched else None


def unfenced_lines(text: str) -> Iterator[str]:
    """Yield document lines outside fenced code blocks."""
    fenced = False
    for line in text.splitlines():
        if line.lstrip().startswith(_FENCE):
            fenced = not fenced
            continue
        if not fenced:
            yield line


def fenced_blocks(text: str, language: str) -> list[str]:
    """Return the body of every fenced block opened with the given info string."""
    blocks: list[str] = []
    collecting = False
    body: list[str] = []
    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped.startswith(_FENCE):
            if collecting:
                body.append(line)
            continue
        if collecting:
            blocks.append("\n".join(body))
            body = []
            collecting = False
            continue
        collecting = stripped[len(_FENCE) :].strip() == language
    return blocks


def parse_fields(lines: list[str]) -> tuple[dict[str, str], tuple[str, ...]]:
    """Return field values with continuation lines preserved, plus repeated keys."""
    fields: dict[str, str] = {}
    repeated: list[str] = []
    key: str | None = None
    for line in lines:
        matched = _FIELD.match(line)
        if matched:
            key = matched.group("key").strip().lower()
            if key in fields:
                repeated.append(key)
            else:
                fields[key] = matched.group("value").strip()
            continue
        stripped = line.strip()
        if key is None or key in repeated:
            continue
        if not stripped or stripped.startswith("#"):
            key = None
            continue
        fields[key] = f"{fields[key]}\n{stripped}" if fields[key] else stripped
    return fields, tuple(repeated)


def read_registry(spec: Path) -> list[Capability]:
    """Read capability rows in their declared implementation order."""
    capabilities: list[Capability] = []
    inside_registry = False
    for line in spec.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside_registry = line.strip() == REGISTRY_HEADING
            continue
        cells = _cells(line) if inside_registry else None
        if not cells or len(cells) < 5:
            continue
        identifier = _CAPABILITY.match(cells[1])
        if identifier:
            capabilities.append(
                Capability(
                    identifier=identifier.group("id"),
                    status=cells[2],
                    evaluation=cells[3],
                    implementation=cells[4],
                )
            )
    return capabilities


def parse_task_block(text: str, *, section: str = "", group: str = "") -> Task | None:
    """Parse one task heading and its metadata, as stored in a record snapshot."""
    lines = text.splitlines()
    for number, line in enumerate(lines):
        matched = _TASK.match(line)
        if not matched:
            continue
        task = Task(
            identifier=matched.group("id"),
            section=section,
            group=group,
            optional=bool(matched.group("optional")),
        )
        task.fields, task.repeated_fields = parse_fields(lines[number + 1 :])
        return task
    return None


def _heading(line: str) -> tuple[str, str, bool] | None:
    if not line.startswith("#"):
        return None
    section = _SECTION.match(line)
    if section:
        return "section", section.group("title"), False
    group = _GROUP.match(line)
    if group:
        return "group", group.group("id"), False
    task = _TASK.match(line)
    if task:
        return "task", task.group("id"), bool(task.group("optional"))
    return "other", "", False


def read_tasks(plan: Path) -> list[Task]:
    """Read tasks in document order with their lane, group, and full metadata."""
    tasks: list[Task] = []
    bodies: list[list[str]] = []
    section = ""
    group = ""
    inside = False
    for line in unfenced_lines(plan.read_text(encoding="utf-8")):
        heading = _heading(line)
        if heading is None:
            if inside:
                bodies[-1].append(line)
            continue
        kind, value, optional = heading
        inside = kind == "task"
        if kind == "section":
            section, group = value, ""
        elif kind == "group":
            group = value
        elif inside:
            tasks.append(Task(identifier=value, section=section, group=group, optional=optional))
            bodies.append([])
    for task, body in zip(tasks, bodies, strict=True):
        task.fields, task.repeated_fields = parse_fields(body)
    return tasks

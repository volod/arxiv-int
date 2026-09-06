"""Offline revision graph, checksum, and frozen-state checks."""

import json
import re
from pathlib import Path

from arxiv_int.contracts.migrations.authoring import (
    file_checksum,
    head_revision,
    read_manifest,
)
from arxiv_int.contracts.migrations.paths import head_state_path, versions_dir
from arxiv_int.contracts.migrations.runner import runner_available

_IGNORED_FILES = frozenset({"__init__.py"})


def _revision_files(project_root: Path) -> dict[str, Path]:
    directory = versions_dir(project_root)
    if not directory.is_dir():
        return {}
    return {
        path.name: path
        for path in sorted(directory.glob("*.py"))
        if path.name not in _IGNORED_FILES
    }


def manifest_findings(project_root: Path) -> list[str]:
    """Fail closed on unlisted, missing, or edited revision files."""
    manifest = read_manifest(project_root)
    revisions = manifest["revisions"]
    files = _revision_files(project_root)
    listed = {str(spec["file"]): revision for revision, spec in revisions.items()}
    findings: list[str] = []
    for name in sorted(set(files) - set(listed)):
        findings.append(f"revision file is not listed in the manifest: {name}")
    for name in sorted(set(listed) - set(files)):
        findings.append(f"manifest lists a missing revision file: {name}")
    for name in sorted(set(files) & set(listed)):
        expected = str(revisions[listed[name]]["sha256"])
        actual = file_checksum(files[name])
        if expected != actual:
            findings.append(
                f"revision {listed[name]} was edited after review: {name} checksum changed"
            )
    return findings


_REVISION = re.compile(r'^revision: str = "(?P<id>[^"]+)"$', re.MULTILINE)
_DOWN_REVISION = re.compile(
    r"^down_revision: str \| None = (?P<parent>None|\"[^\"]+\")$", re.MULTILINE
)


def revision_graph(project_root: Path) -> dict[str, str | None]:
    """Parse revision ids and parents without importing revision modules."""
    graph: dict[str, str | None] = {}
    for name, path in sorted(_revision_files(project_root).items()):
        text = path.read_text(encoding="utf-8")
        identity = _REVISION.search(text)
        parent = _DOWN_REVISION.search(text)
        if identity is None or parent is None:
            raise ValueError(f"revision file has no reviewed revision header: {name}")
        raw = parent.group("parent")
        graph[identity.group("id")] = None if raw == "None" else raw.strip('"')
    return graph


def _walk_findings(graph: dict[str, str | None]) -> list[str]:
    findings: list[str] = []
    for revision, parent in sorted(graph.items()):
        if parent is None:
            continue
        if parent == revision:
            findings.append(f"revision graph is invalid: {revision} is its own parent")
            continue
        if parent not in graph:
            findings.append(f"revision graph is invalid: {revision} names missing parent {parent}")
            continue
        seen = {revision}
        cursor: str | None = parent
        while cursor is not None and cursor in graph:
            if cursor in seen:
                findings.append(f"revision graph is invalid: cycle through {cursor}")
                break
            seen.add(cursor)
            cursor = graph[cursor]
    return sorted(set(findings))


def graph_findings(project_root: Path) -> list[str]:
    """Check parents, cycles, and a single expected head before Alembic loads them."""
    if not runner_available():
        return ["alembic is not installed; the revision graph could not be checked"]
    if not versions_dir(project_root).is_dir():
        return [f"revision graph is invalid: {versions_dir(project_root)} does not exist"]
    try:
        graph = revision_graph(project_root)
    except ValueError as error:
        return [f"revision graph is invalid: {error}"]
    findings = _walk_findings(graph)
    parents = {parent for parent in graph.values() if parent}
    heads = sorted(set(graph) - parents)
    if len(heads) > 1:
        findings.append(f"revision graph has multiple heads: {', '.join(heads)}")
    if findings:
        return findings
    return _alembic_findings(project_root)


def _alembic_findings(project_root: Path) -> list[str]:
    """Cross-check the parsed graph with Alembic's own revision map."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    from arxiv_int.contracts.migrations.paths import script_location

    config = Config()
    config.set_main_option("script_location", str(script_location(project_root)))
    config.set_main_option("path_separator", "os")
    config.set_main_option("version_locations", str(versions_dir(project_root)))
    try:
        scripts = ScriptDirectory.from_config(config)
        list(scripts.walk_revisions())
        heads = scripts.get_heads()
    except Exception as error:  # reported as a finding, never a silent pass
        return [f"revision graph is invalid: {error}"]
    if len(heads) > 1:
        return [f"revision graph has multiple heads: {', '.join(sorted(heads))}"]
    return []


def head_state_findings(project_root: Path) -> list[str]:
    """Require the frozen head state to name the manifest head revision."""
    path = head_state_path(project_root)
    manifest_head = head_revision(read_manifest(project_root))
    if not path.is_file():
        if manifest_head is None:
            return []
        return [f"frozen head state is missing at {path.name}"]
    state = json.loads(path.read_text(encoding="utf-8"))
    recorded = state.get("revision")
    if recorded != manifest_head:
        return [
            f"frozen head state names revision {recorded!r}, "
            f"but the manifest head is {manifest_head!r}"
        ]
    return []

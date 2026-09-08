"""Stage-scoped dependency closure from the installed distribution and uv lock."""

import re
import sys
import tomllib
from collections.abc import Mapping, Sequence
from importlib.metadata import distribution
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.control.asset_hashes import PACKAGE_ROOT


def dependency_assets(project_root: Path, names: Sequence[str]) -> Mapping[str, Any]:
    """Hash selected locked packages and their transitive dependencies without importing them."""
    package = distribution("arxiv-int")
    lock = _load_lock(project_root)
    entries = _closure(lock["package"], names)
    requirements = [item for item in package.requires or () if _requirement_name(item) in entries]
    return {
        "distribution": {"name": package.metadata["Name"], "version": package.version},
        "requirements": sha256_text(normalize_json(sorted(requirements))),
        "python": sys.version,
        "lock_format": [lock["version"], lock.get("revision"), lock["requires-python"]],
        "packages": {name: sha256_text(normalize_json(rows)) for name, rows in entries.items()},
    }


def _load_lock(project_root: Path) -> dict[str, Any]:
    checkout = PACKAGE_ROOT.parents[1]
    use_project = (project_root / "uv.lock").exists() or (project_root / "pyproject.toml").exists()
    path = (project_root if use_project else checkout) / "uv.lock"
    if not path.is_file():
        raise ValueError("stage identity requires uv.lock under the project root")
    with path.open("rb") as stream:
        return tomllib.load(stream)


def _closure(packages: list[dict[str, Any]], names: Sequence[str]) -> dict[str, Any]:
    by_name: dict[str, list[dict[str, Any]]] = {}
    for package in packages:
        by_name.setdefault(str(package["name"]), []).append(package)
    selected: dict[str, Any] = {}
    pending = list(names)
    while pending:
        name = pending.pop()
        if name in selected:
            continue
        if name not in by_name:
            raise ValueError(f"stage dependency missing from uv.lock: {name}")
        rows = sorted(by_name[name], key=normalize_json)
        selected[name] = rows
        pending.extend(_dependency_names(rows))
    return dict(sorted(selected.items()))


def _dependency_names(rows: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for row in rows:
        dependencies = list(row.get("dependencies", ()))
        for optional in row.get("optional-dependencies", {}).values():
            dependencies.extend(optional)
        names.extend(str(item["name"]) for item in dependencies)
    return names


def _requirement_name(requirement: str) -> str:
    return re.split(r"[\[<>=!~; @]", requirement, maxsplit=1)[0].lower().replace("_", "-")

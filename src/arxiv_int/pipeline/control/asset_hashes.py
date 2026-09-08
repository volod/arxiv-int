"""Portable content identities for declared stage assets; no optional runtime imports."""

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from arxiv_int.contracts.catalog.paths import resolve_rooted_reference
from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.pipeline.control.artifacts import hash_file

PACKAGE_ROOT = Path(__file__).resolve().parents[2]


def digest_value(stage: str, field: str, value: Any) -> str:
    """Domain-separate even an empty asset set by stage and owned field."""
    return sha256_text(normalize_json({"stage": stage, "field": field, "value": value}))


def file_hashes(root: Path, references: Sequence[str]) -> dict[str, str]:
    """Hash named files or directory trees with stable relative names; fail closed."""
    result: dict[str, str] = {}
    for reference in sorted(set(references)):
        path = resolve_rooted_reference(root, reference, label="Stage asset")
        if not path.exists():
            raise ValueError(f"missing stage asset: {reference}")
        paths = sorted(path.rglob("*")) if path.is_dir() else [path]
        for item in paths:
            if item.is_symlink() and item.is_dir():
                raise ValueError("stage asset directories must not contain directory symlinks")
            if item.is_dir() or "__pycache__" in item.parts:
                continue
            relative = item.relative_to(root.resolve()).as_posix()
            resolved = resolve_rooted_reference(root, relative, label="Stage asset")
            result[relative] = hash_file(resolved)[0]
    return result

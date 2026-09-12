"""Describe one class, or print the tree, of a frozen scheme for operator inspection."""

import json
from collections.abc import Iterator, Mapping
from typing import Any

from arxiv_int.classification.vocabulary.model import Resolution, Scheme
from arxiv_int.classification.vocabulary.outcomes import NAMESPACE_TAXONOMY, taxonomy_class_id

TREE_INDENT = "  "


def _resolve(scheme: Scheme, target: str) -> Resolution:
    if target in scheme.classes:
        return Resolution(target, target, False)
    resolution = scheme.resolve_code(target)
    if resolution is None:
        raise ValueError(f"{target!r} is neither a class id nor a taxonomy code in this scheme")
    return resolution


def describe_class(
    scheme: Scheme, rows: Mapping[str, Mapping[str, Any]], manifest: Mapping[str, Any], target: str
) -> dict[str, Any]:
    """Return the class, its root-first path with captions, and the scheme identity."""
    resolution = _resolve(scheme, target)
    path = [
        {
            "captions": json.loads(str(rows[class_id]["captions_json"])),
            "classId": class_id,
            "code": rows[class_id]["code"],
            "kind": rows[class_id]["class_kind"],
            "pathToken": rows[class_id]["path_token"],
            "slug": rows[class_id]["slug"],
        }
        for class_id in scheme.path(resolution.class_id)
    ]
    row = rows[resolution.class_id]
    taxonomy = manifest.get("taxonomy") or {}
    return {
        "children": list(scheme.children(resolution.class_id)),
        "classId": resolution.class_id,
        "crosswalk": json.loads(str(row.get("crosswalk_json") or "[]")),
        "extensions": manifest.get("extensions"),
        "namespace": row["namespace"],
        "path": path,
        "requested": target,
        "scheme": {
            "contentSha256": manifest.get("contentSha256"),
            "schemeId": manifest.get("schemeId"),
            "schemeVersion": manifest.get("schemeVersion"),
        },
        "taxonomy": {
            "licence": taxonomy.get("licence"),
            "title": taxonomy.get("title"),
            "version": taxonomy.get("version"),
        },
        "truncated": resolution.truncated,
    }


def tree_lines(scheme: Scheme, root: str | None, depth: int) -> Iterator[str]:
    """Yield ``code  English caption`` lines below an optional root, down to ``depth`` levels."""
    start = taxonomy_class_id(root) if root else None
    if start is not None and start not in scheme.classes:
        raise ValueError(f"taxonomy code {root} is not in this scheme")
    stack = [(class_id, 0) for class_id in reversed(scheme.children(start))]
    if start is not None:
        stack = [(start, 0)]
    while stack:
        class_id, level = stack.pop()
        item = scheme.classes[class_id]
        if item.namespace != NAMESPACE_TAXONOMY:
            continue
        yield f"{TREE_INDENT * level}{item.code}  {item.caption('en') or ''}"
        if level + 1 < depth:
            stack.extend((child, level + 1) for child in reversed(scheme.children(class_id)))

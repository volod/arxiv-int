"""Safe project path resolution.

Adapted under the MIT License from https://github.com/volod/selfsuvis at revision
bd0f4447bf20a72e9421c93f208ce1f52f1c622b.
"""

from collections.abc import Sequence
from pathlib import Path
from typing import Literal

PathKind = Literal["any", "file", "directory"]


def resolve_allowed_path(
    candidate: str | Path,
    allowed_roots: Sequence[str | Path],
    *,
    kind: PathKind = "any",
) -> Path | None:
    """Resolve a path through symlinks and fail closed outside allowed roots."""
    if not allowed_roots:
        return None
    resolved = Path(candidate).expanduser().resolve()
    roots = tuple(Path(root).expanduser().resolve() for root in allowed_roots)
    if not any(resolved == root or root in resolved.parents for root in roots):
        return None
    if kind == "file" and not resolved.is_file():
        return None
    if kind == "directory" and not resolved.is_dir():
        return None
    return resolved

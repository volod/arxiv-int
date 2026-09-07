"""Shared protected-root containment policy for destructive and write actions."""

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from arxiv_int.runtime.config_model import RuntimeConfig

PathKind = Literal["any", "file", "directory"]


@dataclass(frozen=True, slots=True)
class ProtectedRoot:
    """One configured root an action may not erase, write into, or enclose."""

    variable: str
    path: Path
    detail: str
    allow_descendants: bool = False


def contains(root: Path, candidate: Path) -> bool:
    """Report whether a resolved candidate is the root itself or lies beneath it."""
    return candidate == root or root in candidate.parents


def overlaps(left: Path, right: Path) -> bool:
    """Report identical, ancestor, or descendant placement in either direction."""
    return contains(left, right) or contains(right, left)


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
    if not any(contains(root, resolved) for root in roots):
        return None
    if kind == "file" and not resolved.is_file():
        return None
    if kind == "directory" and not resolved.is_dir():
        return None
    return resolved


def containment_violation(candidate: Path, roots: Sequence[ProtectedRoot]) -> ProtectedRoot | None:
    """Return the first protected root a resolved candidate is not allowed to touch."""
    for root in roots:
        if root.allow_descendants and candidate != root.path and contains(root.path, candidate):
            continue
        if overlaps(candidate, root.path):
            return root
    return None


def _source_roots(config: RuntimeConfig) -> list[ProtectedRoot]:
    return [
        ProtectedRoot("PROJECT_ROOT", config.project_root.resolve(), "the project checkout"),
        *(
            ProtectedRoot(silo.variable, silo.root.resolve(), "an archive silo")
            for silo in config.archive_silos
        ),
    ]


def _database_roots(config: RuntimeConfig) -> list[ProtectedRoot]:
    roots = [ProtectedRoot("PGDATA_DIR", config.pgdata_dir.resolve(), "the database cluster")]
    if config.pg_wal_dir is not None:
        roots.append(
            ProtectedRoot("PG_WAL_DIR", config.pg_wal_dir.resolve(), "the database write-ahead log")
        )
    roots.extend(
        ProtectedRoot(f"PG_TABLESPACE_{name.upper()}_DIR", path.resolve(), "a database tablespace")
        for name, path in config.pg_tablespaces
    )
    return roots


def erase_protected_roots(config: RuntimeConfig) -> tuple[ProtectedRoot, ...]:
    """Return roots a service-data reset may never erase or enclose.

    Service-data roots derive from `RESULTS_DIR` by default, so strict descendants of the
    results root stay erasable while the results root itself and any ancestor do not.
    """
    return (
        *_source_roots(config),
        ProtectedRoot(
            "RESULTS_DIR", config.results_dir.resolve(), "the results root", allow_descendants=True
        ),
    )


def report_protected_roots(config: RuntimeConfig) -> tuple[ProtectedRoot, ...]:
    """Return roots a readiness report may never be written into or enclose."""
    return (*_source_roots(config), *_database_roots(config))

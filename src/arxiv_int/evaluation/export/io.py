"""Read verified bundle artifacts and write Git-bound export copies."""

import os
from pathlib import Path, PurePosixPath

from arxiv_int.evaluation.bundles.layout import (
    MANIFEST_NAME,
    list_bundle_tree,
    open_contained_file,
    parse_artifact_name,
    read_capped,
)
from arxiv_int.evaluation.bundles.manifest import canonical_json
from arxiv_int.evaluation.export.errors import ExportPathError
from arxiv_int.evaluation.export.policy import policy_bytes


def _contained_path(name: str) -> PurePosixPath:
    if name == MANIFEST_NAME:
        return PurePosixPath(MANIFEST_NAME)
    return parse_artifact_name(name)


def snapshot_tree(root: Path) -> dict[str, bytes]:
    """Read every regular file in a verified bundle tree."""
    files, _directories = list_bundle_tree(root)
    return {name: read_named(root, name) for name in sorted(files)}


def read_named(root: Path, name: str) -> bytes:
    """Read one contained regular file without following a final symlink."""
    with open_contained_file(root, _contained_path(name)) as fd:
        size = int(os.fstat(fd).st_size)
        if size == 0:
            return b""
        return read_capped(fd, size, label=name)


def write_bytes(path: Path, payload: bytes) -> None:
    """Write a Git-bound copy, creating parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def write_json(path: Path, payload: object) -> None:
    """Write a canonical JSON diagnostic or receipt."""
    write_bytes(path, canonical_json(payload))


def write_policy_copy(path: Path) -> None:
    """Write the committed policy bytes to a diagnostic path."""
    write_bytes(path, policy_bytes())


def relative_destination(path: Path, root: Path | None) -> str:
    """Return a stable posix destination name independent of machine roots."""
    resolved = path.resolve()
    if root is not None:
        try:
            return resolved.relative_to(root.resolve()).as_posix()
        except ValueError:
            pass
    if not path.is_absolute():
        return PurePosixPath(path.as_posix()).as_posix()
    return path.name


def refuse_protected_destination(destination: Path, source_root: Path) -> None:
    """Refuse destinations that would rewrite the source bundle."""
    dest = destination.resolve()
    source = source_root.resolve()
    if dest == source or dest.is_relative_to(source):
        raise ExportPathError("export destination is inside the source bundle")

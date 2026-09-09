"""No-follow directory discovery with memory bounded by the depth limit."""

import os
import stat
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.pipeline.inventory.model import DEFAULT_POLICY, InventoryPolicy


@dataclass(frozen=True, slots=True)
class Entry:
    """One lstat observation; errors and links are explicit, never followed."""

    relative_path: str
    status: str
    signature: tuple[int, ...] = ()


def signature(info: os.stat_result) -> tuple[int, ...]:
    """Fields that detect replacement, permissions and same-size restored-mtime edits."""
    return (
        info.st_dev,
        info.st_ino,
        info.st_mode,
        info.st_size,
        info.st_mtime_ns,
        info.st_ctime_ns,
    )


def walk(root: Path, policy: InventoryPolicy = DEFAULT_POLICY) -> Iterator[Entry]:
    """Stream entries from descriptor-relative directories, including incomplete scopes."""
    try:
        descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError:
        yield Entry(".", "unreadable-directory")
        return
    try:
        yield from _walk(descriptor, "", 0, policy)
    finally:
        os.close(descriptor)


def _walk(descriptor: int, prefix: str, depth: int, policy: InventoryPolicy) -> Iterator[Entry]:
    before = signature(os.fstat(descriptor))
    try:
        with os.scandir(descriptor) as entries:
            for entry in entries:
                relative = f"{prefix}/{entry.name}" if prefix else entry.name
                yield from _entry(descriptor, relative, entry, depth, policy)
    except OSError:
        yield Entry(prefix or ".", "unreadable-directory")
    if before != signature(os.fstat(descriptor)):
        yield Entry(prefix or ".", "unstable-directory")


def _entry(
    descriptor: int, relative: str, entry: os.DirEntry[str], depth: int, policy: InventoryPolicy
) -> Iterator[Entry]:
    try:
        info = entry.stat(follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):
            status = "file" if stat.S_ISREG(info.st_mode) else "unsupported-special"
            if stat.S_ISLNK(info.st_mode):
                status = "link"
            yield Entry(relative, status, signature(info))
        elif depth >= policy.directory_depth:
            yield Entry(relative, "directory-depth-limit", signature(info))
        else:
            child = os.open(
                entry.name, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor
            )
            try:
                yield from _walk(child, relative, depth + 1, policy)
            finally:
                os.close(child)
    except OSError:
        yield Entry(relative, "unreadable", ())


def open_source(root: Path, relative: str) -> int:
    """Open every parent without following links; the caller owns the returned fd."""
    descriptor = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    parts = Path(relative).parts
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
    finally:
        os.close(descriptor)

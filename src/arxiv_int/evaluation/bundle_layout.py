"""Local tree layout, regular-file I/O, and exclusive directory publication."""

import errno
import hashlib
import os
import stat
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path, PurePosixPath

from arxiv_int.evaluation.bundle_errors import BundleExistsError, BundleLayoutError

HASH_CHUNK_BYTES = 1_048_576
MANIFEST_NAME = "manifest.json"
SCORES_NAME = "scores.jsonl"
RESERVED_ARTIFACT_NAMES = frozenset({MANIFEST_NAME, SCORES_NAME})
_NULL = "\x00"
_OPEN_FLAGS = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)


def parse_artifact_name(name: str) -> PurePosixPath:
    """Return a relative posix artifact path that cannot escape or replace the manifest."""
    if not isinstance(name, str) or not name or _NULL in name:
        raise BundleLayoutError(f"invalid bundle artifact name: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or not path.parts or any(part in {"", ".", ".."} for part in path.parts):
        raise BundleLayoutError(f"invalid bundle artifact name: {name!r}")
    if path.as_posix() == MANIFEST_NAME:
        raise BundleLayoutError("manifest.json is reserved")
    return path


def extra_artifact_name(name: str) -> str:
    """Normalize a caller artifact name and refuse names reserved by publication."""
    normalized = parse_artifact_name(name).as_posix()
    if normalized in RESERVED_ARTIFACT_NAMES:
        raise BundleLayoutError(f"reserved bundle artifact name: {name!r}")
    return normalized


def digest_bytes(payload: bytes) -> str:
    """Return the SHA-256 hex digest of an in-memory payload."""
    return hashlib.sha256(payload).hexdigest()


def write_payload(path: Path, payload: bytes) -> tuple[str, int]:
    """Write payload in chunks and return its digest and size without a second slurp."""
    path.parent.mkdir(parents=True, exist_ok=True)
    hasher = hashlib.sha256()
    view = memoryview(payload)
    with path.open("wb") as handle:
        for start in range(0, len(payload), HASH_CHUNK_BYTES):
            chunk = view[start : start + HASH_CHUNK_BYTES]
            handle.write(chunk)
            hasher.update(chunk)
        handle.flush()
    return hasher.hexdigest(), len(payload)


def list_bundle_tree(root: Path) -> tuple[frozenset[str], frozenset[str]]:
    """List relative posix files and directories, refusing symlinks and nonregular entries."""
    files: set[str] = set()
    directories: set[str] = set()
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        current = Path(dirpath)
        for name in dirnames:
            _record_directory(root, current / name, directories)
        for name in filenames:
            _record_file(root, current / name, files)
    return frozenset(files), frozenset(directories)


def parent_directories(names: set[str]) -> frozenset[str]:
    """Return the relative directory prefixes required by artifact paths."""
    prefixes: set[str] = set()
    for name in names:
        parts = PurePosixPath(name).parts
        prefixes.update(PurePosixPath(*parts[:index]).as_posix() for index in range(1, len(parts)))
    return frozenset(prefixes)


def exclusive_publish(staging: Path, destination: Path) -> None:
    """Claim destination and atomically replace that empty claim with staging.

    mkdir is the exclusive name claim. os.replace then swaps the empty directory
    for the verified staging tree on the same filesystem. A leftover empty
    destination from a process crash blocks a later publish rather than being
    replaced. Power-loss durability is not provided: files are flushed but not
    fsynced.
    """
    if destination.is_symlink() or destination.exists():
        raise BundleExistsError(f"run bundle already exists: {destination}")
    try:
        os.mkdir(destination)
    except FileExistsError as error:
        raise BundleExistsError(f"run bundle already exists: {destination}") from error
    try:
        os.replace(staging, destination)
    except OSError as error:
        _release_empty_claim(destination)
        if error.errno in {errno.EEXIST, errno.ENOTEMPTY, errno.EISDIR, errno.EBUSY}:
            raise BundleExistsError(f"run bundle already exists: {destination}") from error
        raise


@contextmanager
def open_contained_file(root: Path, relative: PurePosixPath) -> Iterator[int]:
    """Open a regular file under root without following a final symlink."""
    path = root.joinpath(*relative.parts)
    try:
        fd = os.open(path, _OPEN_FLAGS)
    except OSError as error:
        raise BundleLayoutError(
            f"run-bundle path is not a contained regular file: {relative}"
        ) from error
    try:
        _require_regular_fd(fd, relative)
        _require_contained_fd(fd, root, relative)
        yield fd
    finally:
        os.close(fd)


def digest_fd(fd: int) -> tuple[str, int]:
    """Hash an already-open file descriptor in bounded chunks."""
    hasher = hashlib.sha256()
    total = 0
    while True:
        chunk = os.read(fd, HASH_CHUNK_BYTES)
        if not chunk:
            break
        hasher.update(chunk)
        total += len(chunk)
    return hasher.hexdigest(), total


def read_capped(fd: int, limit: int, *, label: str) -> bytes:
    """Read an opened file entirely only when its size is within ``limit``."""
    size = os.fstat(fd).st_size
    if size > limit:
        raise BundleLayoutError(f"{label} exceeds {limit} bytes")
    payload = os.read(fd, size + 1)
    if len(payload) > limit:
        raise BundleLayoutError(f"{label} exceeds {limit} bytes")
    return payload


def _record_directory(root: Path, path: Path, directories: set[str]) -> None:
    relative = path.relative_to(root).as_posix()
    if path.is_symlink() or not path.is_dir():
        raise BundleLayoutError(f"run-bundle entry is not a regular directory: {relative}")
    directories.add(relative)


def _record_file(root: Path, path: Path, files: set[str]) -> None:
    relative = path.relative_to(root).as_posix()
    if path.is_symlink() or not stat.S_ISREG(path.lstat().st_mode):
        raise BundleLayoutError(f"run-bundle entry is not a regular file: {relative}")
    files.add(relative)


def _require_regular_fd(fd: int, relative: PurePosixPath) -> None:
    if not stat.S_ISREG(os.fstat(fd).st_mode):
        raise BundleLayoutError(f"run-bundle entry is not a regular file: {relative.as_posix()}")


def _require_contained_fd(fd: int, root: Path, relative: PurePosixPath) -> None:
    resolved_root = root.resolve()
    opened = _opened_path(fd, root.joinpath(*relative.parts))
    if not opened.is_relative_to(resolved_root):
        raise BundleLayoutError(f"run-bundle path escapes bundle tree: {relative.as_posix()}")


def _opened_path(fd: int, fallback: Path) -> Path:
    proc = Path("/proc/self/fd") / str(fd)
    try:
        return Path(os.readlink(proc))
    except OSError:
        return fallback.resolve()


def _release_empty_claim(destination: Path) -> None:
    try:
        os.rmdir(destination)
    except OSError:
        return

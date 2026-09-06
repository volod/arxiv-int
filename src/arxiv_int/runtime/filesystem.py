"""Filesystem placement evidence for runtime roots."""

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

NON_OWNING_FILESYSTEMS = frozenset(
    {"9p", "cifs", "exfat", "fuseblk", "msdos", "nfs", "nfs4", "ntfs", "smb3", "vfat"}
)
DATABASE_FILESYSTEMS = frozenset(
    {"btrfs", "ext2", "ext3", "ext4", "overlay", "tmpfs", "xfs", "zfs"}
)


@dataclass(frozen=True, slots=True)
class FilesystemEvidence:
    """Measured placement evidence for one resolved root."""

    path: Path
    filesystem: str
    device_id: str
    rotational: bool | None
    free_bytes: int
    ownership_capable: bool
    read_only: bool


def existing_ancestor(path: Path) -> Path:
    """Return the closest existing path at or above a candidate."""
    candidate = path
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return candidate


def _mount_details(path: Path) -> tuple[str, bool]:
    mountinfo = Path("/proc/self/mountinfo")
    if not mountinfo.is_file():
        return "unknown", False
    best = (Path("/"), "unknown", False)
    for line in mountinfo.read_text(encoding="utf-8").splitlines():
        left, separator, right = line.partition(" - ")
        fields = left.split()
        if not separator or len(fields) < 6:
            continue
        mount = Path(fields[4].replace("\\040", " "))
        if path != mount and mount not in path.parents:
            continue
        filesystem = right.split()[0]
        candidate = (mount, filesystem, "ro" in fields[5].split(","))
        if len(str(mount)) >= len(str(best[0])):
            best = candidate
    return best[1], best[2]


def _rotational(device_id: str) -> bool | None:
    device = Path("/sys/dev/block") / device_id
    if not device.exists():
        return None
    resolved = device.resolve()
    for candidate in (resolved, *resolved.parents):
        flag = candidate / "queue" / "rotational"
        if flag.is_file():
            value = flag.read_text(encoding="ascii").strip()
            return value == "1" if value in {"0", "1"} else None
    return None


def inspect_filesystem(path: Path) -> FilesystemEvidence:
    """Inspect the filesystem containing a path, including an uncreated output path."""
    resolved = path.resolve()
    existing = existing_ancestor(resolved)
    details = existing.stat()
    device_id = f"{os.major(details.st_dev)}:{os.minor(details.st_dev)}"
    filesystem, read_only = _mount_details(existing)
    return FilesystemEvidence(
        path=resolved,
        filesystem=filesystem,
        device_id=device_id,
        rotational=_rotational(device_id),
        free_bytes=shutil.disk_usage(existing).free,
        ownership_capable=filesystem not in NON_OWNING_FILESYSTEMS,
        read_only=read_only,
    )

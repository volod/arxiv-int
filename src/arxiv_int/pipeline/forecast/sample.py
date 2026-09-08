"""Bounded directory metadata sampling and inventory/delta manifest loaders."""

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json, sha256_text
from arxiv_int.interfaces.sources import SiloRoot
from arxiv_int.pipeline.forecast.inputs import InventoryEvidence
from arxiv_int.pipeline.run.persist import load_json

INVENTORY_SCHEMA = "arxiv-int.inventory.v1"
MANIFEST_NAMES = ("manifest.json", "inventory.json")


def sample_silos(
    silos: tuple[SiloRoot, ...],
    *,
    file_limit: int,
) -> InventoryEvidence:
    """Count files and bytes from metadata only; never read file contents."""
    files = 0
    total = 0
    formats: dict[str, list[int]] = {}
    truncated = False
    for silo in silos:
        if truncated:
            break
        if not silo.root.exists():
            continue
        for path in _iter_files(silo.root):
            if files >= file_limit:
                truncated = True
                break
            try:
                size = path.stat().st_size
            except OSError:
                continue
            files += 1
            total += size
            ext = path.suffix.lower().lstrip(".") or "unknown"
            bucket = formats.setdefault(ext, [0, 0])
            bucket[0] += 1
            bucket[1] += size
    mapping = {name: (counts[0], counts[1]) for name, counts in sorted(formats.items())}
    return InventoryEvidence(
        files=files,
        bytes=total,
        added=files,
        changed=0,
        renamed=0,
        removed=0,
        formats=mapping,
        source="sample",
        truncated=truncated,
        fingerprint=_inventory_fingerprint(files, total, mapping, "sample", truncated),
    )


def load_inventory_manifest(path: Path) -> InventoryEvidence | None:
    """Load a captured inventory or delta manifest when present."""
    if not path.is_file():
        return None
    payload = load_json(path)
    return inventory_from_payload(payload, source_hint=path.parent.name)


def resolve_inventory(
    silos: tuple[SiloRoot, ...],
    search_roots: tuple[Path, ...],
    *,
    file_limit: int,
) -> InventoryEvidence:
    """Prefer delta, then inventory manifests, then bounded metadata sampling."""
    delta = _first_manifest(search_roots, ("delta",))
    inventory = _first_manifest(search_roots, ("inventory",))
    if delta is not None:
        return delta
    if inventory is not None:
        return inventory
    return sample_silos(silos, file_limit=file_limit)


def inventory_from_payload(
    payload: dict[str, Any], *, source_hint: str = "inventory"
) -> InventoryEvidence:
    """Parse a fixture or captured inventory object."""
    formats_raw = payload.get("formats", {})
    formats: dict[str, tuple[int, int]] = {}
    if isinstance(formats_raw, dict):
        for name, item in formats_raw.items():
            if isinstance(item, dict):
                formats[str(name)] = (int(item.get("files", 0)), int(item.get("bytes", 0)))
    source = str(payload.get("source") or source_hint)
    if source not in {"sample", "inventory", "delta"}:
        source = "delta" if source_hint == "delta" else "inventory"
    files = int(payload.get("files", 0))
    total = int(payload.get("bytes", 0))
    truncated = bool(payload.get("truncated", False))
    return InventoryEvidence(
        files=files,
        bytes=total,
        added=int(payload.get("added", files)),
        changed=int(payload.get("changed", 0)),
        renamed=int(payload.get("renamed", 0)),
        removed=int(payload.get("removed", 0)),
        formats=formats,
        source=source,
        truncated=truncated,
        fingerprint=str(
            payload.get("fingerprint")
            or _inventory_fingerprint(files, total, formats, source, truncated)
        ),
    )


def _first_manifest(
    search_roots: tuple[Path, ...], directories: Iterable[str]
) -> InventoryEvidence | None:
    for root in search_roots:
        for name in directories:
            for filename in MANIFEST_NAMES:
                loaded = load_inventory_manifest(root / name / filename)
                if loaded is not None:
                    return loaded
    return None


def _iter_files(root: Path) -> Iterable[Path]:
    if root.is_file() and not root.is_symlink():
        yield root
        return
    try:
        entries = sorted(root.iterdir(), key=lambda item: item.name)
    except OSError:
        return
    for entry in entries:
        if entry.is_symlink():
            continue
        if entry.is_dir():
            yield from _iter_files(entry)
        elif entry.is_file():
            yield entry


def _inventory_fingerprint(
    files: int,
    total: int,
    formats: dict[str, tuple[int, int]],
    source: str,
    truncated: bool,
) -> str:
    payload = {
        "bytes": total,
        "files": files,
        "formats": {name: {"bytes": pair[1], "files": pair[0]} for name, pair in formats.items()},
        "source": source,
        "truncated": truncated,
    }
    return sha256_text(normalize_json(payload))

"""Snapshot identities, checksum indexes, and external artifact validation."""

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TextIO

from arxiv_int.pipeline.control.artifacts import hash_file

CONTRACT_VERSION = "1.0.0"


def snapshot_suffix(generation: str, snapshot: str) -> Path:
    """Return the immutable partition suffix shared by one snapshot's roots."""
    return (
        Path(f"contract_version={CONTRACT_VERSION}")
        / f"generation_id={generation}"
        / f"snapshot={snapshot}"
    )


def snapshot_roots(
    results: Path, layout: Mapping[str, str], generation: str, snapshot: str
) -> dict[str, Path]:
    """Bind each logical artifact kind to its immutable product root."""
    suffix = snapshot_suffix(generation, snapshot)
    return {name: results / relative / suffix for name, relative in layout.items()}


def write_json_line(handle: TextIO, value: dict[str, object]) -> None:
    """Write one deterministic ASCII JSON line."""
    handle.write(json.dumps(value, ensure_ascii=True, sort_keys=True) + "\n")


def record_file(handle: TextIO, kind: str, path: Path, root: Path) -> None:
    """Append one rooted artifact checksum to a streamed file index."""
    write_json_line(
        handle,
        {"kind": kind, "path": str(path.relative_to(root)), "sha256": hash_file(path)[0]},
    )


def abort_publication(
    staging: Path, handles: tuple[TextIO, ...], moved: list[Path], sealed: bool
) -> None:
    """Remove unpublished scratch and any roots moved before a failed seal."""
    for handle in handles:
        if not handle.closed:
            handle.close()
    shutil.rmtree(staging, ignore_errors=True)
    if not sealed:
        for path in moved:
            shutil.rmtree(path, ignore_errors=True)


def snapshot_summary(
    schema: str,
    generation: str,
    contracts: Mapping[str, str],
    roots: Mapping[str, Path],
    counts: Mapping[str, int],
    catalog_fingerprint: str,
    files_sha256: str,
) -> dict[str, object]:
    """Build the content-free manifest summary shared by lake producers."""
    return {
        "schema": schema,
        "generation_id": generation,
        "contracts": dict(contracts),
        "roots": {name: str(path) for name, path in roots.items()},
        **counts,
        "pandera": {"status": "pass", "catalog_fingerprint": catalog_fingerprint},
        "files_sha256": files_sha256,
    }


def validate_snapshot_manifest(path: Path, digest: str, *, label: str) -> dict[str, Any]:
    """Rehash every artifact one manifest references before any reuse."""
    if path.is_symlink() or hash_file(path)[0] != digest:
        raise ValueError(f"{label} manifest identity mismatch")
    summary: dict[str, Any] = json.loads(path.read_text(encoding="ascii"))
    index = path.parent / "files.jsonl"
    if index.is_symlink() or hash_file(index)[0] != summary["files_sha256"]:
        raise ValueError(f"{label} file index mismatch")
    roots = {name: Path(value) for name, value in summary["roots"].items()}
    with index.open(encoding="ascii") as handle:
        for line in handle:
            record = json.loads(line)
            relative = Path(record["path"])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError(f"invalid {label} artifact path")
            artifact = roots[record["kind"]] / relative
            if artifact.is_symlink() or hash_file(artifact)[0] != record["sha256"]:
                raise ValueError(f"{label} artifact checksum mismatch")
    return summary


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    """Read one small validated JSON-lines sidecar into memory."""
    with path.open(encoding="ascii") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def batch_sidecar(parquet_path: Path, key: str) -> dict[str, dict[str, Any]]:
    """Index one batch metadata sidecar by the identity its rows carry."""
    path = parquet_path.with_name(f"{parquet_path.stem}.metadata.jsonl")
    if not path.is_file():
        raise ValueError(f"batch {parquet_path.name} is missing its metadata sidecar")
    return {str(item[key]): item for item in read_jsonl(path)}

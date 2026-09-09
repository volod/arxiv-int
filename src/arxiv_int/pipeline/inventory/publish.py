"""Atomic bounded Parquet partitions and a streamed checksum index, sealed last."""

import json
import os
from importlib import import_module
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from arxiv_int.pipeline.control.artifacts import hash_file
from arxiv_int.pipeline.dag.cancel import check_cancelled
from arxiv_int.pipeline.inventory.checkpoint import Checkpoint
from arxiv_int.pipeline.inventory.model import InventoryPolicy, Observation

if TYPE_CHECKING:
    from arxiv_int.pipeline.inventory.validate import InventoryValidator

BUCKETS = "0123456789abcdef"


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    """Seal a small operational manifest with ASCII JSON and fsync."""
    temporary = path.with_name(f".{path.name}.tmp")
    with temporary.open("w", encoding="ascii") as handle:
        json.dump(payload, handle, ensure_ascii=True, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def publish(
    checkpoint: Checkpoint,
    root: Path,
    validator: "InventoryValidator",
    policy: InventoryPolicy,
    generation: str,
    silos: frozenset[str],
    scope: dict[str, bool],
) -> Path:
    """Publish a new immutable snapshot, keeping every batch and index bounded."""
    snapshot = root / f"snapshot={uuid4().hex}"
    snapshot.mkdir()
    total = 0
    with (snapshot / ".partitions.jsonl.tmp").open("w", encoding="ascii") as index:
        for bucket in BUCKETS:
            items: list[Observation] = []
            part = 0
            for item in checkpoint.observations(bucket):
                check_cancelled()
                items.append(item)
                if len(items) == policy.batch_rows:
                    record = _batch(snapshot, bucket, part, items, validator, generation, silos)
                    index.write(json.dumps(record, sort_keys=True) + "\n")
                    total += len(items)
                    items.clear()
                    part += 1
            if items:
                record = _batch(snapshot, bucket, part, items, validator, generation, silos)
                index.write(json.dumps(record, sort_keys=True) + "\n")
                total += len(items)
        index.flush()
        os.fsync(index.fileno())
    (snapshot / ".partitions.jsonl.tmp").replace(snapshot / "partitions.jsonl")
    counts = {silo: checkpoint.counts(silo) for silo in sorted(silos)}
    summary = {
        "schema": "arxiv-int.streaming-inventory.v1",
        "generation_id": generation,
        "contract_id": "source-occurrences",
        "contract_version": "1.0.0",
        "rows": total,
        "totals": checkpoint.counts(),
        "silos": counts,
        "completed_source_set": scope,
        "global_occurrence_keys": {
            "status": "pass",
            "checked_rows": total,
            "backend": "sqlite-primary-key",
        },
        "pandera": {
            "status": "pass",
            "checked_rows": total,
            "catalog_fingerprint": validator.fingerprint,
        },
        "partitions_sha256": hash_file(snapshot / "partitions.jsonl")[0],
    }
    atomic_json(snapshot / "inventory.json", summary)
    return snapshot / "inventory.json"


def _batch(
    snapshot: Path,
    bucket: str,
    part: int,
    items: list[Observation],
    validator: "InventoryValidator",
    generation: str,
    silos: frozenset[str],
) -> dict[str, Any]:
    table = validator.batch(items, generation, generation, silos)
    stem = f"bucket-{bucket}-part-{part:08d}"
    parquet = import_module("pyarrow.parquet")
    destination = snapshot / f"{stem}.parquet"
    temporary = snapshot / f".{stem}.tmp"
    with parquet.ParquetWriter(temporary, validator.arrow_schema, compression="zstd") as writer:
        writer.write_table(table)
    with temporary.open("rb") as handle:
        os.fsync(handle.fileno())
    temporary.replace(destination)
    metadata = snapshot / f"{stem}.metadata.jsonl"
    with metadata.open("w", encoding="ascii") as handle:
        for item in items:
            handle.write(json.dumps(item.metadata(), ensure_ascii=True, sort_keys=True) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return {
        "rows": len(items),
        "parquet": destination.name,
        "parquet_sha256": hash_file(destination)[0],
        "metadata": metadata.name,
        "metadata_sha256": hash_file(metadata)[0],
    }


def validate_manifest(path: Path, digest: str) -> dict[str, Any]:
    """Rehash every external partition before accepting a stage cache hit."""
    if path.is_symlink() or path.name != "inventory.json" or hash_file(path)[0] != digest:
        raise ValueError("inventory manifest identity mismatch")
    summary: dict[str, Any] = json.loads(path.read_text(encoding="ascii"))
    index = path.parent / "partitions.jsonl"
    if index.is_symlink() or hash_file(index)[0] != summary["partitions_sha256"]:
        raise ValueError("inventory partition index mismatch")
    rows = 0
    with index.open(encoding="ascii") as handle:
        for line in handle:
            record = json.loads(line)
            rows += record["rows"]
            for kind in ("parquet", "metadata"):
                name = record[kind]
                if Path(name).name != name:
                    raise ValueError("invalid inventory partition path")
                partition = path.parent / name
                if partition.is_symlink() or hash_file(partition)[0] != record[f"{kind}_sha256"]:
                    raise ValueError("inventory partition checksum mismatch")
    if rows != summary["rows"]:
        raise ValueError("inventory row count mismatch")
    return summary

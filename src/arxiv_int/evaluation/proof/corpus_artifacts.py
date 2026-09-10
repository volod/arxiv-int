"""Read and revalidate corpus snapshots using their producer contracts."""

from collections.abc import Iterator, Mapping
from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.evaluation.evaluate.errors import ProofIntegrityError
from arxiv_int.pipeline.control.artifacts import hash_file, validate_attempt
from arxiv_int.pipeline.inventory.model import Observation
from arxiv_int.pipeline.inventory.publish import validate_manifest as validate_inventory
from arxiv_int.pipeline.inventory.validate import InventoryValidator
from arxiv_int.pipeline.lake.artifacts import batch_sidecar, read_jsonl, validate_snapshot_manifest
from arxiv_int.pipeline.lake.validate import SnapshotValidator
from arxiv_int.pipeline.quality.evidence import validate_quality_evidence
from arxiv_int.pipeline.run.persist import StageExecution, load_json

STAGES = ("inventory", "extract", "normalize", "dedupe", "chunk")
DATASETS = {
    "extract": ("documents", "spans"),
    "normalize": ("normalized-documents",),
    "dedupe": ("duplicate-groups",),
    "chunk": ("chunks",),
}


def require(condition: bool, message: str) -> None:
    """Refuse incomplete or inconsistent proof evidence."""
    if not condition:
        raise ProofIntegrityError(message)


def rows(root: Path, key: str) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """Stream bounded Parquet batches with their exact metadata peers."""
    parquet = import_module("pyarrow.parquet")
    for path in sorted(root.glob("*.parquet")):
        metadata = batch_sidecar(path, key)
        observed: set[str] = set()
        for batch in parquet.ParquetFile(path).iter_batches(batch_size=256):
            for row in batch.to_pylist():
                identity = str(row[key])
                require(
                    identity in metadata and identity not in observed, "metadata identity mismatch"
                )
                observed.add(identity)
                yield row, metadata[identity]
        require(observed == set(metadata), "unaccounted metadata rows")


def validate_execution(item: StageExecution, project_root: Path) -> tuple[Path, dict[str, Any]]:
    """Require passed attempt, current contract checks and checksum-valid external artifacts."""
    require(item.status in {"succeeded", "quarantined"}, "stage did not succeed")
    require(item.outcome in {"produced", "empty"}, "stage is partial or failed")
    directory = Path(item.directory or "")
    validate_attempt(directory, reuse_key=item.reuse_key, attempt=item.attempt)
    payload = load_json(directory / "stage.json")
    outputs = payload["outputs"]
    require(bool(outputs), "stage has no dataset output")
    generation = outputs[0]["generationId"]
    require(validate_quality_evidence(directory, generation), "stage quality evidence failed")
    pointer = outputs[0]["partition"]
    path = Path(pointer["manifest"])
    if item.stage == "inventory":
        summary = validate_inventory(path, pointer["sha256"])
        validate_inventory_rows(path, summary, project_root)
    else:
        summary = validate_snapshot_manifest(path, pointer["sha256"], label=item.stage)
        validate_contracts(summary, DATASETS[item.stage], project_root)
    require(summary["pandera"]["status"] == "pass", "missing Pandera evidence")
    return path, summary


def validate_contracts(summary: Mapping[str, Any], contracts: tuple[str, ...], root: Path) -> None:
    """Execute generated Pandera batch rules and complete-snapshot identity checks again."""
    validator = SnapshotValidator(root, contracts)
    parquet = import_module("pyarrow.parquet")
    for contract in contracts:
        directory = Path(summary["roots"][contract])
        for path in sorted(directory.glob("part-*.parquet")):
            for batch in parquet.ParquetFile(path).iter_batches(batch_size=256):
                validator[contract].batch(batch.to_pylist())
        validator.check_identities(contract, directory)


def validate_inventory_rows(path: Path, summary: Mapping[str, Any], root: Path) -> None:
    """Reconcile inventory metadata, physical rows and contract provenance."""
    validator = InventoryValidator(root)
    identities: set[str] = set()
    silos = frozenset(summary["silos"])
    for row, extra in rows(path.parent, "occurrence_id"):
        identity = str(extra["occurrence_id"])
        require(identity not in identities, "duplicate inventory occurrence")
        identities.add(identity)
        observation = Observation(
            **{key: value for key, value in extra.items() if key != "occurrence_id"}
        )
        expected = observation.contract_row(row["scan_id"], row["generation_id"])
        require(expected == row, "inventory metadata does not match contract row")
        validator.batch([observation], row["scan_id"], row["generation_id"], silos)
    require(len(identities) == summary["rows"], "inventory count mismatch")
    require(all(summary["completed_source_set"].values()), "inventory source scope is incomplete")


def snapshot_files(path: Path, summary: Mapping[str, Any]) -> Iterator[Path]:
    """Enumerate exactly the sealed files, excluding checkpoint scratch."""
    yield path
    if path.name == "inventory.json":
        index = path.parent / "partitions.jsonl"
        yield index
        for item in read_jsonl(index):
            yield path.parent / item["parquet"]
            yield path.parent / item["metadata"]
    else:
        index = path.parent / "files.jsonl"
        yield index
        for item in read_jsonl(index):
            yield Path(summary["roots"][item["kind"]]) / item["path"]


def artifact_record(path: Path) -> dict[str, int | str]:
    """Return a streamed file digest and byte size."""
    digest, size = hash_file(path)
    return {"sha256": digest, "bytes": size}

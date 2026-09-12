"""Join checksum-validated inventory, extraction, and normalization snapshots by stable ids."""

import json
from collections import defaultdict
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Any

from arxiv_int.classification.model import DocumentText, PhysicalFile
from arxiv_int.extraction.artifacts import validate_manifest as validate_extraction_manifest
from arxiv_int.interfaces.pipeline import StageContext
from arxiv_int.pipeline.inventory.publish import validate_manifest as validate_inventory_manifest
from arxiv_int.pipeline.lake.artifacts import batch_sidecar
from arxiv_int.pipeline.normalize.artifacts import (
    DOCUMENTS_KIND,
    view_path,
)
from arxiv_int.pipeline.normalize.artifacts import (
    validate_manifest as validate_normalization_manifest,
)

_PARQUET_BATCH_ROWS = 128


def _reference(context: StageContext, name: str) -> tuple[Path, str]:
    path = context.options.get(f"{name}_manifest", "")
    digest = context.options.get(f"{name}_manifest_sha256", "")
    if not path or not digest:
        raise ValueError(f"classify requires a validated upstream {name} manifest")
    manifest = Path(path)
    if manifest.is_symlink() or manifest.resolve() != manifest:
        raise ValueError(f"symlinked {name} manifest reference")
    return manifest, digest


def source_snapshots(context: StageContext) -> dict[str, dict[str, Any]]:
    """Validate the entire upstream identity chain and return its summaries."""
    inventory_path, inventory_digest = _reference(context, "inventory")
    normalization_path, normalization_digest = _reference(context, "normalization")
    inventory = validate_inventory_manifest(inventory_path, inventory_digest)
    normalization = validate_normalization_manifest(normalization_path, normalization_digest)
    extraction_ref = normalization.get("extraction")
    if not isinstance(extraction_ref, dict):
        raise ValueError("normalization manifest has no extraction identity")
    extraction_path = Path(str(extraction_ref.get("manifest") or ""))
    extraction_digest = str(extraction_ref.get("sha256") or "")
    extraction = validate_extraction_manifest(extraction_path, extraction_digest)
    return {
        "inventory": {**inventory, "manifest": str(inventory_path), "sha256": inventory_digest},
        "extraction": {
            **extraction,
            "manifest": str(extraction_path),
            "sha256": extraction_digest,
        },
        "normalization": {
            **normalization,
            "manifest": str(normalization_path),
            "sha256": normalization_digest,
        },
    }


@dataclass(frozen=True, slots=True)
class _DocumentLocator:
    document_id: str
    normalized_document_id: str
    title: str
    text_path: Path


def physical_files(
    snapshots: Mapping[str, Mapping[str, Any]], *, max_text_chars: int
) -> Iterator[PhysicalFile]:
    """Stream every physical inventory row exactly once with all usable container text."""
    documents = _normalized_documents(snapshots["normalization"])
    extraction = snapshots["extraction"]
    extraction_roots = {name: Path(str(value)) for name, value in extraction["roots"].items()}
    mapped: dict[tuple[str, str], list[str]] = defaultdict(list)
    occurrence_file = extraction_roots["documents"] / "occurrences.jsonl"
    for row in _jsonl(occurrence_file):
        mapped[(str(row["silo_id"]), str(row["relative_path"]))].append(str(row["document_id"]))
    failures: dict[tuple[str, str], list[str]] = defaultdict(list)
    for row in _jsonl(extraction_roots["quarantine"] / "quarantine.jsonl"):
        failures[(str(row["silo_id"]), str(row["relative_path"]))].append(
            f"extraction-{row['reason']}"
        )
    normalization_failures = {
        str(row["document_id"]): f"normalization-{row['reason']}"
        for row in _jsonl(
            Path(str(snapshots["normalization"]["roots"]["quarantine"])) / "quarantine.jsonl"
        )
    }
    inventory_path = Path(str(snapshots["inventory"]["manifest"]))
    for metadata in sorted(inventory_path.parent.glob("*.metadata.jsonl")):
        for row in _jsonl(metadata):
            if row.get("members"):
                continue
            key = (str(row["silo_id"]), str(row["relative_path"]))
            document_ids = tuple(dict.fromkeys(mapped.get(key, ())))
            available, truncated = _read_documents(document_ids, documents, max_text_chars)
            missing = tuple(
                normalization_failures.get(item, f"normalization-missing:{item}")
                for item in document_ids
                if item not in documents
            )
            yield PhysicalFile(
                occurrence_id=str(row["occurrence_id"]),
                silo_id=key[0],
                relative_path=key[1],
                content_hash=row.get("content_hash"),
                status=str(row.get("status") or "quarantined"),
                reason=None if row.get("reason") is None else str(row["reason"]),
                documents=available,
                extraction_failures=tuple(failures.get(key, ())) + missing,
                truncated_document_ids=truncated,
            )


def _normalized_documents(summary: Mapping[str, Any]) -> dict[str, _DocumentLocator]:
    roots = {name: Path(str(value)) for name, value in summary["roots"].items()}
    documents = roots[DOCUMENTS_KIND]
    parquet = import_module("pyarrow.parquet")
    polars = import_module("polars")
    found: dict[str, _DocumentLocator] = {}
    for path in sorted(documents.glob("part-*.parquet")):
        sidecar = batch_sidecar(path, "normalized_document_id")
        reader = parquet.ParquetFile(path)
        for batch in reader.iter_batches(batch_size=_PARQUET_BATCH_ROWS):
            frame = polars.from_arrow(batch).select(
                polars.col("document_id").cast(polars.String),
                polars.col("normalized_document_id").cast(polars.String),
            )
            for row in frame.to_dicts():
                identity = str(row["normalized_document_id"])
                document_id = str(row["document_id"])
                extra = sidecar.get(identity, {})
                found[document_id] = _DocumentLocator(
                    document_id,
                    identity,
                    str(extra.get("title") or ""),
                    view_path(documents, "search", identity),
                )
    return found


def _read_documents(
    document_ids: tuple[str, ...],
    locators: Mapping[str, _DocumentLocator],
    max_text_chars: int,
) -> tuple[tuple[DocumentText, ...], tuple[str, ...]]:
    """Read at most one file-level character budget across a container and its members.

    The second element names every present document the budget cut short or skipped, so a
    partial read is a recorded denominator instead of a silent omission.
    """
    remaining = max_text_chars
    found = []
    truncated = []
    for document_id in document_ids:
        locator = locators.get(document_id)
        if locator is None:
            continue
        if locator.text_path.is_symlink() or not locator.text_path.is_file():
            raise ValueError("normalized search view is not a real file")
        if remaining <= 0:
            truncated.append(locator.document_id)
            continue
        with locator.text_path.open(encoding="utf-8") as handle:
            text = handle.read(remaining)
            clipped = bool(handle.read(1))
        remaining -= len(text)
        if clipped:
            truncated.append(locator.document_id)
        found.append(
            DocumentText(
                locator.document_id,
                locator.normalized_document_id,
                locator.title,
                text,
            )
        )
    return tuple(found), tuple(truncated)


def _jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open(encoding="ascii") as handle:
        for line in handle:
            if line.strip():
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path.name} contains a non-object row")
                yield value

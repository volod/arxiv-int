"""Read published attempt files, partitions, anchors, and lake listings."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from arxiv_int.inspect.lookup import relative_posix
from arxiv_int.inspect.model import (
    AnchorSummary,
    FileSummary,
    PartitionSummary,
    StageSummary,
)
from arxiv_int.inspect.quality import (
    MANIFEST_KEYS,
    STAGE_KEYS,
    conformance,
    load_quality,
    payload_drifted,
)
from arxiv_int.observability.logging.redact import extra_secrets_from_env, redact_text
from arxiv_int.pipeline.control.artifacts import ArtifactPublishError, validate_attempt
from arxiv_int.pipeline.run.persist import StageExecution, load_json


def stage_summary(
    directory: Path,
    runs_dir: Path,
    item: StageExecution | None,
    versions: Mapping[str, str],
    limit: int,
    dataset: str,
    stage_name: str,
) -> StageSummary | None:
    """Summarize one attempt directory; skip when a dataset filter misses it."""
    files, tree_valid, manifest_drift = file_summaries(directory)
    payload, stage_drift = stage_payload(directory)
    partitions = output_partitions(payload, versions, limit)
    if dataset and not any(part.dataset == dataset for part in partitions):
        return None
    checks, lineage, quality_drift = load_quality(directory)
    anchors = anchor_summaries(payload, directory, limit)
    outcome = str(payload.get("outcome") or (item.outcome if item else "failed"))
    status = item.status if item else "unknown"
    failed_detail = (item.detail,) if item is not None and item.status == "failed" else ()
    failures = _safe_failures(failed_detail)
    quarantines = tuple(check.rule_id for check in checks if check.status == "warning")
    if status == "quarantined" and not quarantines:
        quarantines = (stage_name,)
    drifted = manifest_drift or stage_drift or quality_drift
    drifted = drifted or any(part.conformance == "drifted" for part in partitions)
    return StageSummary(
        stage_name,
        status,
        outcome,
        directory.parent.name,
        item.attempt if item else attempt_number(directory),
        bool(item.cache_hit) if item else False,
        sum(file.bytes for file in files),
        relative_posix(directory, runs_dir),
        files[:limit],
        partitions[:limit],
        checks[:limit],
        lineage[:limit],
        anchors[:limit],
        quarantines[:limit],
        failures[:limit],
        drifted,
        tree_valid,
    )


def missing_attempt(item: StageExecution, dataset: str) -> StageSummary | None:
    """Summarize a ledger row that has no readable attempt tree."""
    if dataset:
        return None
    return StageSummary(
        item.stage,
        item.status,
        item.outcome,
        "default",
        item.attempt,
        item.cache_hit,
        item.bytes,
        "<path>" if item.directory else "",
        (),
        (),
        (),
        (),
        (),
        (item.stage,) if item.status == "quarantined" else (),
        _safe_failures((item.detail,) if item.status == "failed" else ()),
        False,
        False,
    )


def file_summaries(directory: Path) -> tuple[tuple[FileSummary, ...], bool, bool]:
    """Read manifest checksums without rewriting files."""
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return (), False, True
    try:
        payload = load_json(manifest_path)
    except (OSError, ValueError):
        return (), False, True
    files_spec = payload.get("files")
    if not isinstance(files_spec, dict):
        return (), False, True
    valid = tree_valid(directory, payload)
    rows: list[FileSummary] = []
    for name, spec in sorted(files_spec.items()):
        if not isinstance(spec, dict):
            continue
        row_count = spec.get("rowCount")
        if row_count is None:
            row_count = spec.get("row_count")
        rows.append(
            FileSummary(
                str(name),
                optional_int(spec.get("bytes")) or 0,
                str(spec.get("sha256") or ""),
                optional_int(row_count),
                valid,
            )
        )
    return tuple(rows), valid, payload_drifted(payload, MANIFEST_KEYS)


def tree_valid(directory: Path, payload: Mapping[str, Any]) -> bool:
    """Re-check checksums in place; never rewrite the tree."""
    try:
        validate_attempt(
            directory,
            reuse_key=str(payload.get("reuseKey") or ""),
            attempt=int(payload.get("attempt") or 0),
        )
    except (ArtifactPublishError, OSError, TypeError, ValueError):
        return False
    return True


def stage_payload(directory: Path) -> tuple[dict[str, Any], bool]:
    """Load stage.json or report it missing/malformed."""
    path = directory / "stage.json"
    if not path.is_file():
        return {}, True
    try:
        payload = load_json(path)
    except (OSError, ValueError):
        return {}, True
    return payload, payload_drifted(payload, STAGE_KEYS)


def output_partitions(
    payload: Mapping[str, Any], versions: Mapping[str, str], limit: int
) -> tuple[PartitionSummary, ...]:
    """Map stage outputs onto contract conformance without locating lake files."""
    rows: list[PartitionSummary] = []
    for item in payload.get("outputs") or ():
        if not isinstance(item, dict) or len(rows) >= limit:
            continue
        dataset = str(item.get("dataset") or "")
        version = str(item.get("contractVersion") or item.get("contract_version") or "")
        generation = str(item.get("generationId") or item.get("generation_id") or "")
        partition = item.get("partition")
        raw = partition if isinstance(partition, dict) else {}
        pairs = tuple(sorted((str(key), str(value)) for key, value in raw.items()))
        rows.append(
            PartitionSummary(
                dataset,
                version,
                pairs,
                generation,
                conformance(dataset, version, versions),
                0,
                None,
            )
        )
    return tuple(rows)


def anchor_summaries(
    payload: Mapping[str, Any], directory: Path, limit: int
) -> tuple[AnchorSummary, ...]:
    """Collect bounded anchors from stage.json or a published sidecar."""
    raw = payload.get("anchors")
    if not isinstance(raw, list):
        raw = _sidecar_anchors(directory)
    rows: list[AnchorSummary] = []
    for item in raw:
        if not isinstance(item, dict) or len(rows) >= limit:
            continue
        occurrence = item.get("occurrence")
        if not isinstance(occurrence, dict):
            occurrence = item
        rows.append(
            AnchorSummary(
                str(occurrence.get("silo_id") or occurrence.get("siloId") or ""),
                str(occurrence.get("relative_path") or occurrence.get("relativePath") or ""),
                str(occurrence.get("scan_id") or occurrence.get("scanId") or ""),
                str(item.get("kind") or ""),
                optional_int(item.get("page")),
                str(item.get("sheet") or ""),
                str(item.get("cell_range") or item.get("cellRange") or ""),
            )
        )
    return tuple(rows)


def attempt_number(directory: Path) -> int:
    """Parse ``attempt-N`` directory names."""
    prefix, _sep, suffix = directory.name.partition("-")
    if prefix != "attempt":
        return 0
    try:
        return int(suffix)
    except ValueError:
        return 0


def _safe_failures(details: tuple[str, ...]) -> tuple[str, ...]:
    secrets = extra_secrets_from_env()
    return tuple(redact_text(detail, secrets) for detail in details if detail)


def optional_int(value: object) -> int | None:
    """Parse an optional integer field."""
    if value is None or value == "":
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _sidecar_anchors(directory: Path) -> list[Any]:
    sidecar = directory / "anchors.json"
    if not sidecar.is_file():
        return []
    try:
        loaded = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return loaded if isinstance(loaded, list) else []

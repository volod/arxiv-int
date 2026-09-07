"""Export identity-obfuscated Git-bound copies from a verified proof bundle."""

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from arxiv_int.evaluation.bundle_errors import BundleError
from arxiv_int.evaluation.bundle_layout import digest_bytes
from arxiv_int.evaluation.bundle_manifest import MANIFEST_NAME
from arxiv_int.evaluation.bundles import verify_run_bundle
from arxiv_int.evaluation.export_catalog import (
    IdentityCatalog,
    empty_catalog,
    parse_identity_catalog,
)
from arxiv_int.evaluation.export_checks import classify_artifact, decode_text, refuse_leaks
from arxiv_int.evaluation.export_errors import ExportCatalogError, ExportError, ExportPathError
from arxiv_int.evaluation.export_io import (
    refuse_protected_destination,
    snapshot_tree,
    write_bytes,
    write_json,
)
from arxiv_int.evaluation.export_map import SubstitutionTable, build_substitution_table
from arxiv_int.evaluation.export_policy import IDENTITIES_ARTIFACT, RESERVED_EXPORT_ARTIFACTS
from arxiv_int.evaluation.export_receipt import build_receipt, write_diagnostics
from arxiv_int.evaluation.export_rewrite import (
    MappedText,
    encode_json,
    encode_jsonl,
    mark_transformed_manifest,
    rewrite_json_value,
    rewrite_text,
)


@dataclass(frozen=True, slots=True)
class ExportMapping:
    """One source-bundle artifact copied to an explicit Git-bound path."""

    source: str
    destination: Path


@dataclass(frozen=True, slots=True)
class ExportRequest:
    """Verified bundle, explicit file list, and diagnostic run identity."""

    source_bundle: Path
    mappings: tuple[ExportMapping, ...]
    run_id: str
    project_root: Path
    destination_root: Path | None = None
    receipt: Path | None = None


@dataclass(frozen=True, slots=True)
class PublishedExport:
    """Identity-free fingerprints of one Git-bound export."""

    source_fingerprint: str
    export_fingerprint: str
    policy_fingerprint: str
    files: tuple[tuple[str, Path], ...]
    diagnostics: Path


def export_proof_bundle(request: ExportRequest) -> PublishedExport:
    """Rewrite selected artifacts without mutating the source bundle."""
    source = Path(request.source_bundle)
    try:
        source_fingerprint = verify_run_bundle(source)
    except BundleError as error:
        raise ExportError(str(error)) from error
    original = snapshot_tree(source)
    mappings = resolve_mappings(request, original, source)
    catalog = load_catalog(original)
    for item in mappings:
        classify_artifact(item.source, original[item.source])
    decoded = {item.source: decode_text(original[item.source]) for item in mappings}
    table = build_substitution_table(catalog, decoded)
    transformed = transform_artifacts(mappings, original, decoded, table)
    for payload in transformed.values():
        refuse_leaks(payload, table.needles)
    for item in mappings:
        write_bytes(item.destination, transformed[item.source])
    if snapshot_tree(source) != original:
        raise ExportPathError("source bundle bytes changed during export")
    files = tuple((item.source, item.destination) for item in mappings)
    receipt = build_receipt(
        source_fingerprint=source_fingerprint,
        files=files,
        transformed=transformed,
        destination_root=request.destination_root,
        project_root=request.project_root,
    )
    diagnostics = write_diagnostics(
        project_root=request.project_root,
        run_id=request.run_id,
        catalog=catalog,
        table=table,
        receipt=receipt,
    )
    if request.receipt is not None:
        receipt_path = _resolve_path(request.receipt, request)
        refuse_protected_destination(receipt_path, source)
        write_json(receipt_path, receipt)
    return PublishedExport(
        source_fingerprint,
        str(receipt["export_fingerprint"]),
        str(receipt["policy_fingerprint"]),
        files,
        diagnostics,
    )


def resolve_mappings(
    request: ExportRequest, original: Mapping[str, bytes], source: Path
) -> tuple[ExportMapping, ...]:
    """Resolve destinations and refuse reserved or missing sources."""
    if not request.mappings:
        raise ExportPathError("export file list is empty")
    seen_source: set[str] = set()
    seen_dest: set[Path] = set()
    resolved: list[ExportMapping] = []
    for item in sorted(request.mappings, key=lambda mapping: mapping.source):
        if item.source in RESERVED_EXPORT_ARTIFACTS:
            raise ExportPathError(f"raw identity artifact cannot be exported: {item.source}")
        if item.source not in original:
            raise ExportPathError(f"source artifact is not in the bundle: {item.source}")
        if item.source in seen_source:
            raise ExportPathError(f"duplicate source artifact: {item.source}")
        destination = _resolve_path(item.destination, request)
        if destination in seen_dest:
            raise ExportPathError(f"duplicate export destination: {destination}")
        refuse_protected_destination(destination, source)
        seen_source.add(item.source)
        seen_dest.add(destination)
        resolved.append(ExportMapping(item.source, destination))
    return tuple(resolved)


def load_catalog(original: Mapping[str, bytes]) -> IdentityCatalog:
    """Load `identities.json` or an empty catalog for synthetic fixtures."""
    if IDENTITIES_ARTIFACT not in original:
        return empty_catalog()
    try:
        payload = json.loads(decode_text(original[IDENTITIES_ARTIFACT]))
    except (json.JSONDecodeError, ExportError) as error:
        raise ExportCatalogError("identities.json is not valid JSON") from error
    return parse_identity_catalog(payload)


def transform_artifacts(
    mappings: Sequence[ExportMapping],
    original: Mapping[str, bytes],
    decoded: Mapping[str, str],
    table: SubstitutionTable,
) -> dict[str, bytes]:
    """Rewrite text first so JSON spans can join the same substitutes."""
    kinds = {
        item.source: classify_artifact(item.source, original[item.source]) for item in mappings
    }
    artifact_maps: dict[str, MappedText] = {}
    transformed: dict[str, bytes] = {}
    for item in mappings:
        if kinds[item.source] != "text":
            continue
        spans = tuple(span for span in table.spans if span.artifact == item.source)
        mapped = rewrite_text(decoded[item.source], table, spans=spans)
        artifact_maps[item.source] = mapped
        transformed[item.source] = mapped.text.encode("utf-8")
    checksums = {
        name: (digest_bytes(payload), len(payload)) for name, payload in transformed.items()
    }
    for item in mappings:
        if kinds[item.source] == "text" or item.source == MANIFEST_NAME:
            continue
        payload = transform_json(
            item.source, decoded[item.source], kinds[item.source], table, artifact_maps, checksums
        )
        transformed[item.source] = payload
        checksums[item.source] = (digest_bytes(payload), len(payload))
    if MANIFEST_NAME in kinds:
        transformed[MANIFEST_NAME] = transform_json(
            MANIFEST_NAME, decoded[MANIFEST_NAME], "json", table, artifact_maps, checksums
        )
    return transformed


def transform_json(
    name: str,
    text: str,
    kind: str,
    table: SubstitutionTable,
    artifact_maps: Mapping[str, MappedText],
    checksums: Mapping[str, tuple[str, int]],
) -> bytes:
    """Rewrite one JSON or JSONL artifact and rebuild manifest checksums."""
    try:
        if kind == "jsonl":
            rows = [json.loads(line) for line in text.splitlines() if line]
            return encode_jsonl([rewrite_json_value(row, table, artifact_maps) for row in rows])
        payload = json.loads(text)
    except json.JSONDecodeError as error:
        raise ExportCatalogError(f"{name} is not valid JSON") from error
    rewritten = rewrite_json_value(payload, table, artifact_maps)
    if name == MANIFEST_NAME and isinstance(rewritten, dict):
        rewritten = mark_transformed_manifest(rewritten, checksums)
    if not isinstance(rewritten, (dict, list)):
        raise ExportCatalogError(f"{name} is not a JSON object or array")
    return encode_json(rewritten)


def _resolve_path(path: Path, request: ExportRequest) -> Path:
    if path.is_absolute():
        return path.resolve()
    root = request.destination_root or request.project_root
    return (root / path).resolve()

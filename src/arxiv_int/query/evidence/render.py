"""Secret-free console and JSON rendering for evidence resolution."""

from collections.abc import Iterable, Mapping
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.observability.logging.redact import extra_secrets_from_env, redact_text
from arxiv_int.query.evidence.model import (
    EvidenceAnchor,
    EvidenceResolution,
    ImportReport,
    SourceLocation,
)

_BLOCKED = frozenset({"prompt", "text", "document", "body", "password", "secret", "token"})


def console_lines(resolution: EvidenceResolution) -> tuple[str, ...]:
    """Render ASCII operator lines with redacted details."""
    secrets = extra_secrets_from_env()
    lines = [
        f"schema={resolution.schema}",
        f"kind={resolution.citation.kind}",
        f"citation_id={resolution.citation.citation_id}",
        f"document_id={resolution.document_id or 'none'}",
        f"content_hash={resolution.content_hash or 'none'}",
        f"ambiguous={str(resolution.ambiguous).lower()}",
        f"locations={len(resolution.locations)}",
    ]
    if resolution.extractor_profile:
        lines.append(f"extractor_profile={resolution.extractor_profile}")
    for location in resolution.locations:
        lines.append(_location_line(location, secrets))
    if resolution.original_anchor is not None:
        lines.append(_anchor_line("original", resolution.original_anchor))
    if resolution.normalized_anchor is not None:
        lines.append(_anchor_line("normalized", resolution.normalized_anchor))
    for finding in resolution.findings:
        lines.append(f"finding={_safe(finding, secrets)}")
    return tuple(lines)


def json_document(resolution: EvidenceResolution) -> str:
    """Return canonical redacted JSON for one resolution."""
    secrets = extra_secrets_from_env()
    return normalize_json(redact_tree(_payload(resolution), secrets))


def import_lines(report: ImportReport) -> tuple[str, ...]:
    """Render ASCII lines for one ledger import."""
    lines = [
        f"schema={report.schema}",
        f"ledger_id={report.ledger_id or 'none'}",
        f"inserted={report.inserted}",
        f"skipped={report.skipped}",
        f"refused={report.refused}",
    ]
    lines.extend(f"finding={item}" for item in report.findings)
    return tuple(lines)


def redact_tree(value: object, secrets: Iterable[str]) -> object:
    """Recursively redact strings and blocked keys."""
    if isinstance(value, Mapping):
        result: dict[str, object] = {}
        for key, item in value.items():
            if str(key).lower() in _BLOCKED:
                result[str(key)] = "<redacted>"
            else:
                result[str(key)] = redact_tree(item, secrets)
        return result
    if isinstance(value, list):
        return [redact_tree(item, secrets) for item in value]
    if isinstance(value, str):
        return _safe(value, secrets)
    return value


def _payload(resolution: EvidenceResolution) -> dict[str, Any]:
    citation = resolution.citation
    return {
        "ambiguous": resolution.ambiguous,
        "citation": {
            "citation_id": citation.citation_id,
            "document_id": citation.document_id,
            "fact_id": citation.fact_id,
            "kind": citation.kind,
            "report_id": citation.report_id,
            "span_id": citation.span_id,
        },
        "content_hash": resolution.content_hash,
        "document_id": resolution.document_id,
        "extractor_profile": resolution.extractor_profile,
        "findings": list(resolution.findings),
        "locations": [_location_payload(item) for item in resolution.locations],
        "normalized_anchor": _anchor_payload(resolution.normalized_anchor),
        "original_anchor": _anchor_payload(resolution.original_anchor),
        "schema": resolution.schema,
    }


def _location_payload(item: SourceLocation) -> dict[str, str]:
    return {
        "container_path": item.container_path,
        "content_hash": item.content_hash,
        "current_path": item.current_path,
        "member_path": item.member_path,
        "occurrence_id": item.occurrence_id,
        "original_path": item.original_path,
        "role": item.role,
        "scan_id": item.scan_id,
        "silo_id": item.silo_id,
        "status": item.status,
    }


def _anchor_payload(item: EvidenceAnchor | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "cell_range": item.cell_range,
        "column": item.column,
        "container_path": item.container_path,
        "end_char": item.end_char,
        "kind": item.kind,
        "member_path": item.member_path,
        "page": item.page,
        "row": item.row,
        "sheet": item.sheet,
        "space": item.space,
        "start_char": item.start_char,
    }


def _location_line(item: SourceLocation, secrets: Iterable[str]) -> str:
    member = f" member={item.member_path}" if item.member_path else ""
    return _safe(
        f"location silo={item.silo_id} original={item.original_path} "
        f"current={item.current_path} status={item.status} role={item.role}{member}",
        secrets,
    )


def _anchor_line(label: str, item: EvidenceAnchor) -> str:
    parts = [f"anchor_{label} space={item.space} kind={item.kind or 'none'}"]
    if item.page is not None:
        parts.append(f"page={item.page}")
    if item.sheet:
        parts.append(f"sheet={item.sheet}")
    if item.cell_range:
        parts.append(f"cell={item.cell_range}")
    if item.member_path:
        parts.append(f"member={item.member_path}")
    return " ".join(parts)


def _safe(text: str, secrets: Iterable[str]) -> str:
    return redact_text(text, secrets)

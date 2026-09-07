"""JSON codec for knowledge-base documents."""

from collections.abc import Mapping
from typing import Any

from arxiv_int.pipeline.publish.model import SCHEMA_ID, Coverage, KnowledgeBase, OutputEntry


def document_payload(document: KnowledgeBase) -> dict[str, Any]:
    """Serialize a knowledge-base document with stable keys."""
    return {
        "active": document.active,
        "catalog_path": document.catalog_path,
        "config_fingerprint": document.config_fingerprint,
        "coverage": {
            "empty": document.coverage.empty,
            "failed": document.coverage.failed,
            "missing": document.coverage.missing,
            "not_selected": document.coverage.not_selected,
            "partial": document.coverage.partial,
            "produced": document.coverage.produced,
            "required_families": document.coverage.required_families,
        },
        "fingerprint": document.fingerprint,
        "generation_id": document.generation_id,
        "limitations": list(document.limitations),
        "not_selected": list(document.not_selected),
        "outputs": [_output_payload(item) for item in document.outputs],
        "profile": document.profile,
        "report_path": document.report_path,
        "resume_command": document.resume_command,
        "run_id": document.run_id,
        "schema": document.schema,
        "source_snapshot": document.source_snapshot,
        "status": document.status,
        "status_command": document.status_command,
    }


def document_from_payload(payload: Mapping[str, Any]) -> KnowledgeBase:
    """Load a knowledge-base document from JSON."""
    coverage = payload["coverage"]
    if not isinstance(coverage, Mapping):
        raise ValueError("coverage is not an object")
    return KnowledgeBase(
        schema=str(payload.get("schema", SCHEMA_ID)),
        run_id=str(payload["run_id"]),
        generation_id=str(payload["generation_id"]),
        profile=str(payload["profile"]),
        status=str(payload["status"]),
        active=bool(payload.get("active", False)),
        source_snapshot=str(payload["source_snapshot"]),
        config_fingerprint=str(payload["config_fingerprint"]),
        fingerprint=str(payload.get("fingerprint", "")),
        outputs=tuple(_output_from_payload(item) for item in payload.get("outputs", ())),
        coverage=Coverage(
            int(coverage["required_families"]),
            int(coverage["produced"]),
            int(coverage["empty"]),
            int(coverage["partial"]),
            int(coverage["failed"]),
            int(coverage["missing"]),
            int(coverage["not_selected"]),
        ),
        limitations=tuple(str(item) for item in payload.get("limitations", ())),
        not_selected=tuple(str(item) for item in payload.get("not_selected", ())),
        report_path=str(payload.get("report_path", "")),
        status_command=str(payload.get("status_command", "")),
        resume_command=str(payload.get("resume_command", "")),
        catalog_path=str(payload.get("catalog_path", "")),
    )


def _output_payload(item: OutputEntry) -> dict[str, Any]:
    return {
        "bytes": item.bytes,
        "checksum": item.checksum,
        "family": item.family,
        "outcome": item.outcome,
        "path": item.path,
        "required": item.required,
        "row_count": item.row_count,
        "stage": item.stage,
    }


def _output_from_payload(item: object) -> OutputEntry:
    if not isinstance(item, Mapping):
        raise ValueError("output entry is not an object")
    row = item.get("row_count")
    return OutputEntry(
        str(item["family"]),
        str(item["stage"]),
        str(item["path"]),
        str(item["checksum"]),
        int(item.get("bytes", 0)),
        None if row is None else int(row),
        str(item["outcome"]),
        bool(item.get("required", True)),
    )

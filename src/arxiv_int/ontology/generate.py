"""Deterministic ontology binding generation."""

import hashlib
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.ontology.catalog import OntologyCatalog
from arxiv_int.ontology.load import load_manifest, load_ontology_catalog
from arxiv_int.ontology.paths import ontology_root_for


def _sha256_text(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _canonical_bytes(document: Any) -> bytes:
    return normalize_json(document).encode("utf-8")


def _class_rows(catalog: OntologyCatalog) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in sorted(catalog.classes.values(), key=lambda value: value.term_id):
        rows.append(
            {
                "termId": item.term_id,
                "uri": item.uri,
                "kind": "class",
                "status": item.status,
                "labels": dict(sorted(item.labels.items())),
                "parents": list(item.parents),
                "disjointWith": list(item.disjoint_with),
            }
        )
    return rows


def _predicate_rows(catalog: OntologyCatalog) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in sorted(catalog.predicates.values(), key=lambda value: value.term_id):
        rows.append(
            {
                "termId": item.term_id,
                "uri": item.uri,
                "kind": item.kind,
                "status": item.status,
                "contractBinding": item.contract_binding,
                "labels": dict(sorted(item.labels.items())),
                "domains": list(item.domains),
                "ranges": list(item.ranges),
                "functional": item.functional,
                "deprecated": item.deprecated,
                "successor": item.successor,
                "quantityKind": item.quantity_kind,
                "canonicalUnit": item.canonical_unit,
            }
        )
    return rows


def build_bindings_documents(catalog: OntologyCatalog) -> dict[str, dict[str, Any]]:
    """Build deterministic ontology.* binding documents."""
    classes = _class_rows(catalog)
    predicates = _predicate_rows(catalog)
    catalog_doc = {
        "ontologyId": catalog.ontology_id,
        "version": catalog.version,
        "classes": classes,
        "predicates": predicates,
        "semanticMatches": {
            key: list(value) for key, value in sorted(catalog.semantic_matches.items())
        },
    }
    terms = []
    for row in classes + predicates:
        terms.append(
            {
                "term_id": row["termId"],
                "uri": row["uri"],
                "label": (row.get("labels") or {}).get("en")
                or (row.get("labels") or {}).get("und")
                or row["termId"],
                "kind": row["kind"],
                "domain_uri": (row.get("domains") or [None])[0] if row["kind"] != "class" else None,
                "range_uri": (row.get("ranges") or [None])[0] if row["kind"] != "class" else None,
                "ontology_version": catalog.version,
                "contract_binding": row.get("contractBinding"),
                "status": row["status"],
            }
        )
    bindings = {
        "ontologyId": catalog.ontology_id,
        "version": catalog.version,
        "activePredicates": [
            {
                "termId": row["termId"],
                "uri": row["uri"],
                "contractBinding": row["contractBinding"],
            }
            for row in predicates
            if row["status"] == "active"
        ],
    }
    return {
        "ontology.catalog.json": catalog_doc,
        "ontology.terms.json": {
            "ontologyId": catalog.ontology_id,
            "version": catalog.version,
            "terms": terms,
        },
        "ontology.bindings.json": bindings,
    }


def generate_ontology_bindings(
    ontology_root: Path | None = None,
    *,
    output_dir: Path | None = None,
) -> dict[str, str]:
    """Write generated ontology.* bindings and return relative path fingerprints."""
    root = ontology_root if ontology_root is not None else ontology_root_for()
    manifest = load_manifest(root)
    catalog = load_ontology_catalog(root)
    documents = build_bindings_documents(catalog)
    target = output_dir
    if target is None:
        target = root / str(manifest.get("generatedDir", "generated"))
    target.mkdir(parents=True, exist_ok=True)
    fingerprints: dict[str, str] = {}
    for name, document in documents.items():
        payload = _canonical_bytes(document)
        path = target / name
        path.write_bytes(payload)
        fingerprints[name] = _sha256_text(payload.decode("utf-8"))
    manifest_doc = {
        "ontologyId": catalog.ontology_id,
        "version": catalog.version,
        "files": fingerprints,
    }
    manifest_payload = _canonical_bytes(manifest_doc)
    (target / "manifest.json").write_bytes(manifest_payload)
    fingerprints["manifest.json"] = _sha256_text(manifest_payload.decode("utf-8"))
    return fingerprints


def check_generation_drift(ontology_root: Path | None = None) -> list[str]:
    """Regenerate into memory and compare against committed generated files."""
    root = ontology_root if ontology_root is not None else ontology_root_for()
    manifest = load_manifest(root)
    generated_dir = root / str(manifest.get("generatedDir", "generated"))
    catalog = load_ontology_catalog(root)
    expected = build_bindings_documents(catalog)
    findings: list[str] = []
    for name, document in expected.items():
        path = generated_dir / name
        if not path.is_file():
            findings.append(f"missing generated ontology binding: {name}")
            continue
        if path.read_bytes() != _canonical_bytes(document):
            findings.append(f"ontology binding drift: {name}")
    manifest_path = generated_dir / "manifest.json"
    if not manifest_path.is_file():
        findings.append("missing generated ontology binding: manifest.json")
    return findings

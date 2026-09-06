"""Ontology evolution classification aligned with contract evolution policy."""

import json
from pathlib import Path
from typing import Any

from arxiv_int.contracts.generate.normalize import normalize_json
from arxiv_int.ontology.catalog import OntologyCatalog
from arxiv_int.ontology.generate import build_bindings_documents
from arxiv_int.ontology.load import load_manifest, load_ontology_catalog
from arxiv_int.ontology.paths import ontology_root_for

ONTOLOGY_IDENTICAL = "identical"
ONTOLOGY_ADDITIVE = "additive"
ONTOLOGY_BREAKING = "breaking"

_PREDICATE_BREAK_FIELDS = ("uri", "kind", "domains", "ranges", "functional", "contractBinding")
_CLASS_BREAK_FIELDS = ("uri", "parents", "disjointWith")


def ontology_snapshot(catalog: OntologyCatalog) -> dict[str, Any]:
    """Freeze the reviewable ontology surface for evolution comparison."""
    documents = build_bindings_documents(catalog)
    return {
        "ontologyId": catalog.ontology_id,
        "version": catalog.version,
        "catalog": documents["ontology.catalog.json"],
        "bindings": documents["ontology.bindings.json"],
    }


def _predicate_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    predicates = ((snapshot.get("catalog") or {}).get("predicates")) or []
    return {str(item["termId"]): item for item in predicates if "termId" in item}


def _class_map(snapshot: dict[str, Any]) -> dict[str, dict[str, Any]]:
    classes = ((snapshot.get("catalog") or {}).get("classes")) or []
    return {str(item["termId"]): item for item in classes if "termId" in item}


def _field_change_detail(term_id: str, field: str) -> str:
    if field == "uri":
        return f"predicate '{term_id}' uri changed without stable alias"
    return f"predicate '{term_id}' field '{field}' changed"


def _one_predicate_break(
    term_id: str, baseline_pred: dict[str, Any], current_pred: dict[str, Any] | None
) -> list[str]:
    if current_pred is None:
        if baseline_pred.get("status") == "active":
            return [f"removed active predicate '{term_id}'"]
        return []
    details = [
        _field_change_detail(term_id, field)
        for field in _PREDICATE_BREAK_FIELDS
        if baseline_pred.get(field) != current_pred.get(field)
    ]
    if (
        baseline_pred.get("status") == "active"
        and current_pred.get("status") == "deprecated"
        and not current_pred.get("successor")
    ):
        details.append(f"predicate '{term_id}' deprecated without successor")
    return details


def _predicate_break_details(
    base_preds: dict[str, dict[str, Any]], cur_preds: dict[str, dict[str, Any]]
) -> list[str]:
    details: list[str] = []
    for term_id, baseline_pred in base_preds.items():
        details.extend(_one_predicate_break(term_id, baseline_pred, cur_preds.get(term_id)))
    return details


def _class_break_details(
    base_classes: dict[str, dict[str, Any]], cur_classes: dict[str, dict[str, Any]]
) -> list[str]:
    details: list[str] = []
    for term_id, baseline_class in base_classes.items():
        current_class = cur_classes.get(term_id)
        if current_class is None:
            if baseline_class.get("status") == "active":
                details.append(f"removed active class '{term_id}'")
            continue
        for field in _CLASS_BREAK_FIELDS:
            if baseline_class.get(field) != current_class.get(field):
                details.append(f"class '{term_id}' field '{field}' changed")
    return details


def _additive_details(
    base_preds: dict[str, dict[str, Any]],
    cur_preds: dict[str, dict[str, Any]],
    base_classes: dict[str, dict[str, Any]],
    cur_classes: dict[str, dict[str, Any]],
) -> list[str]:
    details: list[str] = []
    for term_id in cur_preds:
        if term_id not in base_preds:
            details.append(f"added predicate '{term_id}'")
    for term_id in cur_classes:
        if term_id not in base_classes:
            details.append(f"added class '{term_id}'")
    return details


def classify_ontology_evolution(
    baseline: dict[str, Any], current: dict[str, Any]
) -> tuple[str, tuple[str, ...]]:
    """Classify ontology change as identical, additive, or breaking."""
    base_preds = _predicate_map(baseline)
    cur_preds = _predicate_map(current)
    base_classes = _class_map(baseline)
    cur_classes = _class_map(current)
    breaking = _predicate_break_details(base_preds, cur_preds) + _class_break_details(
        base_classes, cur_classes
    )
    if breaking:
        return ONTOLOGY_BREAKING, tuple(breaking)
    additive = _additive_details(base_preds, cur_preds, base_classes, cur_classes)
    if additive:
        return ONTOLOGY_ADDITIVE, tuple(additive)
    if normalize_json(baseline) == normalize_json(current):
        return ONTOLOGY_IDENTICAL, ()
    return ONTOLOGY_ADDITIVE, ("non-breaking ontology metadata change",)


def version_policy_errors(change: str, baseline_version: str, current_version: str) -> list[str]:
    """Fail closed when ontology version bumps do not match the change class."""
    findings: list[str] = []
    if change == ONTOLOGY_IDENTICAL and baseline_version != current_version:
        findings.append(
            f"identical ontology change must keep version {baseline_version}, got {current_version}"
        )
    if change == ONTOLOGY_ADDITIVE:
        if _major(baseline_version) != _major(current_version):
            findings.append("additive ontology change must not bump major version")
        if _cmp_version(current_version, baseline_version) <= 0:
            findings.append("additive ontology change requires a minor/patch bump")
    if change == ONTOLOGY_BREAKING and _major(current_version) <= _major(baseline_version):
        findings.append("breaking ontology change requires a major version bump")
    return findings


def _parts(version: str) -> tuple[int, int, int]:
    chunks = version.split(".")
    numbers = [int(chunk) for chunk in chunks[:3]]
    while len(numbers) < 3:
        numbers.append(0)
    return numbers[0], numbers[1], numbers[2]


def _major(version: str) -> int:
    return _parts(version)[0]


def _cmp_version(left: str, right: str) -> int:
    left_parts = _parts(left)
    right_parts = _parts(right)
    if left_parts < right_parts:
        return -1
    if left_parts > right_parts:
        return 1
    return 0


def load_evolution_baseline(ontology_root: Path | None = None) -> dict[str, Any]:
    """Load the reviewed ontology evolution baseline."""
    root = ontology_root if ontology_root is not None else ontology_root_for()
    manifest = load_manifest(root)
    path = root / str(manifest.get("evolutionBaseline", "evolution/baseline.json"))
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"ontology evolution baseline must be an object: {path}")
    return payload


def write_evolution_baseline(ontology_root: Path | None = None) -> Path:
    """Write the current ontology snapshot as the reviewed baseline."""
    root = ontology_root if ontology_root is not None else ontology_root_for()
    manifest = load_manifest(root)
    path = root / str(manifest.get("evolutionBaseline", "evolution/baseline.json"))
    path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = ontology_snapshot(load_ontology_catalog(root))
    path.write_text(normalize_json(snapshot), encoding="utf-8")
    return path


def check_ontology_evolution(ontology_root: Path | None = None) -> list[str]:
    """Compare the live ontology against its reviewed evolution baseline."""
    root = ontology_root if ontology_root is not None else ontology_root_for()
    manifest = load_manifest(root)
    baseline_path = root / str(manifest.get("evolutionBaseline", "evolution/baseline.json"))
    if not baseline_path.is_file():
        return [f"missing ontology evolution baseline: {baseline_path}"]
    baseline = load_evolution_baseline(root)
    current = ontology_snapshot(load_ontology_catalog(root))
    change, details = classify_ontology_evolution(baseline, current)
    findings = list(details) if change == ONTOLOGY_BREAKING else []
    findings.extend(
        version_policy_errors(
            change,
            str(baseline.get("version", "")),
            str(current.get("version", "")),
        )
    )
    if change != ONTOLOGY_IDENTICAL and change != ONTOLOGY_BREAKING:
        findings.append(
            "ontology differs from reviewed baseline "
            f"({change}); refresh ontology/evolution/baseline.json after review"
        )
    return findings

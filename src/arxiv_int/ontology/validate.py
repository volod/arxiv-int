"""Application-level ontology validation for fact assertions."""

from dataclasses import dataclass

from arxiv_int.ontology.catalog import OntologyCatalog, OntologyPredicate

_XSD_STRING = "http://www.w3.org/2001/XMLSchema#string"


@dataclass(frozen=True)
class FactAssertion:
    """One subject-predicate-object or subject-predicate-literal claim."""

    subject_id: str
    subject_types: tuple[str, ...]
    predicate: str
    object_id: str | None = None
    object_types: tuple[str, ...] = ()
    literal_value: str | None = None
    literal_datatype: str | None = None


def _resolve_types(catalog: OntologyCatalog, types: tuple[str, ...]) -> frozenset[str]:
    resolved: set[str] = set()
    for type_key in types:
        item = catalog.class_by_uri_or_term(type_key)
        if item is None:
            resolved.add(type_key)
            continue
        resolved.update(catalog.subclass_closure(item.uri))
    return frozenset(resolved)


def _matches_domain_or_range(
    candidate_types: frozenset[str], required_uris: tuple[str, ...]
) -> bool:
    if not required_uris:
        return True
    xsd = "http://www.w3.org/2001/XMLSchema#"
    class_requirements = tuple(uri for uri in required_uris if not uri.startswith(xsd))
    if not class_requirements:
        return True
    return any(required in candidate_types for required in class_requirements)


def _disjoint_conflict(catalog: OntologyCatalog, type_closure: frozenset[str]) -> str | None:
    for uri in type_closure:
        item = catalog.classes.get(uri)
        if item is None:
            continue
        for other in item.disjoint_with:
            if other in type_closure:
                return f"disjoint types {uri} and {other}"
    return None


def _functional_violation(
    predicate: OntologyPredicate,
    assertion: FactAssertion,
    all_assertions: tuple[FactAssertion, ...],
) -> bool:
    if not predicate.functional:
        return False
    matches = [
        item
        for item in all_assertions
        if item.subject_id == assertion.subject_id
        and item.predicate in {assertion.predicate, predicate.uri, predicate.term_id}
    ]
    return len(matches) > 1


def _range_literal_ok(predicate: OntologyPredicate, datatype: str | None) -> bool:
    if predicate.kind != "datatype":
        return False
    if not predicate.ranges:
        return True
    if datatype is None:
        return _XSD_STRING in predicate.ranges
    return datatype in predicate.ranges


def _predicate_status_finding(
    assertion: FactAssertion,
    predicate: OntologyPredicate,
    *,
    allow_deprecated: bool,
) -> str | None:
    if predicate.status == "active":
        return None
    if allow_deprecated and predicate.status == "deprecated":
        return None
    return f"{assertion.subject_id}: predicate '{predicate.term_id}' status is {predicate.status}"


def _object_value_findings(
    catalog: OntologyCatalog,
    assertion: FactAssertion,
    predicate: OntologyPredicate,
) -> list[str]:
    findings: list[str] = []
    if predicate.kind != "object":
        findings.append(
            f"{assertion.subject_id}: datatype predicate '{predicate.term_id}' "
            "cannot take an object id"
        )
        return findings
    object_types = _resolve_types(catalog, assertion.object_types)
    object_conflict = _disjoint_conflict(catalog, object_types)
    if object_conflict and assertion.object_id is not None:
        findings.append(f"{assertion.object_id}: {object_conflict}")
    if not _matches_domain_or_range(object_types, predicate.ranges):
        findings.append(
            f"{assertion.subject_id}: range mismatch for predicate '{predicate.term_id}'"
        )
    return findings


def _literal_value_findings(
    assertion: FactAssertion,
    predicate: OntologyPredicate,
) -> list[str]:
    findings: list[str] = []
    if predicate.kind != "datatype":
        findings.append(
            f"{assertion.subject_id}: object predicate '{predicate.term_id}' cannot take a literal"
        )
        return findings
    if not _range_literal_ok(predicate, assertion.literal_datatype):
        findings.append(
            f"{assertion.subject_id}: literal datatype mismatch for predicate '{predicate.term_id}'"
        )
        return findings
    if predicate.term_id != "pred.confidence-score" or assertion.literal_value is None:
        return findings
    try:
        score = float(assertion.literal_value)
    except ValueError:
        findings.append(f"{assertion.subject_id}: confidence score is not numeric")
        return findings
    if score < 0.0 or score > 1.0:
        findings.append(f"{assertion.subject_id}: confidence score out of range [0, 1]")
    return findings


def _assertion_findings(
    catalog: OntologyCatalog,
    assertion: FactAssertion,
    all_assertions: tuple[FactAssertion, ...],
    *,
    allow_deprecated: bool,
) -> list[str]:
    findings: list[str] = []
    predicate = catalog.predicate_by_uri_or_term(assertion.predicate)
    if predicate is None:
        return [f"{assertion.subject_id}: unknown predicate '{assertion.predicate}'"]
    status_finding = _predicate_status_finding(
        assertion, predicate, allow_deprecated=allow_deprecated
    )
    if status_finding is not None:
        return [status_finding]
    subject_types = _resolve_types(catalog, assertion.subject_types)
    conflict = _disjoint_conflict(catalog, subject_types)
    if conflict:
        findings.append(f"{assertion.subject_id}: {conflict}")
    if not _matches_domain_or_range(subject_types, predicate.domains):
        findings.append(
            f"{assertion.subject_id}: domain mismatch for predicate '{predicate.term_id}'"
        )
    has_object = assertion.object_id is not None
    has_literal = assertion.literal_value is not None
    if has_object == has_literal:
        findings.append(
            f"{assertion.subject_id}: predicate '{predicate.term_id}' needs exactly one "
            "of object_id or literal_value"
        )
        return findings
    if has_object:
        findings.extend(_object_value_findings(catalog, assertion, predicate))
    else:
        findings.extend(_literal_value_findings(assertion, predicate))
    if _functional_violation(predicate, assertion, all_assertions):
        message = (
            f"{assertion.subject_id}: functional predicate '{predicate.term_id}' "
            "has multiple values"
        )
        if message not in findings:
            findings.append(message)
    return findings


def validate_assertions(
    catalog: OntologyCatalog,
    assertions: tuple[FactAssertion, ...] | list[FactAssertion],
    *,
    allow_deprecated: bool = False,
) -> list[str]:
    """Validate assertions against domain/range, disjoint, and functional rules."""
    items = tuple(assertions)
    findings: list[str] = []
    for assertion in items:
        findings.extend(
            _assertion_findings(catalog, assertion, items, allow_deprecated=allow_deprecated)
        )
    return findings

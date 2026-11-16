"""Structural validation of scheme classes and licence metadata.

Errors (duplicate ids, orphaned or cyclic parents, namespace collisions, codes that disagree with
their id, kind or parent, missing required captions, token collisions, missing licences) block
publication.
"""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from arxiv_int.classification.vocabulary.codes import CodeError, kind_for, parent_code
from arxiv_int.classification.vocabulary.model import SchemeClass
from arxiv_int.classification.vocabulary.outcomes import (
    EXCEPTIONAL_OUTCOMES,
    EXTENSION_PREFIX,
    NAMESPACE_EXTENSION,
    NAMESPACE_OUTCOME,
    NAMESPACE_TAXONOMY,
    NAMESPACES,
    namespace_of,
    taxonomy_class_id,
)
from arxiv_int.classification.vocabulary.policy import Licence, SchemePolicy
from arxiv_int.classification.vocabulary.tokens import TokenError, class_id_from_token, class_token

SEVERITY_ERROR = "error"
SEVERITY_WARNING = "warning"
EXTENSION_NAME = re.compile(r"[a-z][a-z0-9-]{1,47}")


@dataclass(frozen=True, slots=True)
class Finding:
    """One validation result tied to a class id when applicable."""

    code: str
    severity: str
    class_id: str | None
    message: str


def errors(findings: Sequence[Finding]) -> tuple[Finding, ...]:
    """Return only blocking findings."""
    return tuple(item for item in findings if item.severity == SEVERITY_ERROR)


def error(code: str, class_id: str | None, message: str) -> Finding:
    """Return one blocking finding."""
    return Finding(code, SEVERITY_ERROR, class_id, message)


def _taxonomy_findings(item: SchemeClass) -> list[Finding]:
    if item.code is None or taxonomy_class_id(item.code) != item.class_id:
        return [error("code-mismatch", item.class_id, "class id must be tax:<code>")]
    try:
        kind = kind_for(item.code)
        parent = parent_code(item.code)
    except CodeError as problem:
        return [error("invalid-code", item.class_id, str(problem))]
    found: list[Finding] = []
    if item.kind != kind:
        found.append(error("invalid-code", item.class_id, f"kind {item.kind} != {kind}"))
    expected = taxonomy_class_id(parent) if parent else None
    if item.parent_id != expected:
        found.append(error("code-mismatch", item.class_id, f"parent must be {expected}"))
    return found


def _extension_findings(item: SchemeClass) -> list[Finding]:
    name = item.class_id[len(EXTENSION_PREFIX) :]
    found: list[Finding] = []
    if EXTENSION_NAME.fullmatch(name) is None:
        found.append(error("extension-name", item.class_id, "name must match [a-z][a-z0-9-]+"))
    if name in EXCEPTIONAL_OUTCOMES or name in NAMESPACES:
        found.append(error("namespace-collision", item.class_id, "name reuses a reserved id"))
    if item.code is not None:
        found.append(error("namespace-collision", item.class_id, "extensions carry no code"))
    if item.parent_id is None or item.parent_id in EXCEPTIONAL_OUTCOMES:
        found.append(error("orphan-parent", item.class_id, "extensions need a tax/ext parent"))
    return found


def _namespace_findings(item: SchemeClass) -> list[Finding]:
    try:
        namespace = namespace_of(item.class_id)
    except ValueError as problem:
        return [error("namespace-collision", item.class_id, str(problem))]
    if namespace != item.namespace:
        return [error("namespace-collision", item.class_id, f"declared {item.namespace}")]
    if namespace == NAMESPACE_TAXONOMY:
        return _taxonomy_findings(item)
    if namespace == NAMESPACE_EXTENSION:
        return _extension_findings(item)
    if item.parent_id is not None or item.code is not None:
        return [error("namespace-collision", item.class_id, "outcomes have no parent or code")]
    return []


def _cycle_findings(classes: Sequence[SchemeClass]) -> list[Finding]:
    parents = {item.class_id: item.parent_id for item in classes}
    looping: set[str] = set()
    for start in parents:
        seen: list[str] = []
        current: str | None = start
        while current is not None and current in parents and current not in seen:
            seen.append(current)
            current = parents[current]
        if current is not None and current in seen:
            looping.update(seen[seen.index(current) :])
    return [error("cycle", class_id, "parent links loop") for class_id in sorted(looping)]


def _token_findings(classes: Sequence[SchemeClass], max_bytes: int) -> list[Finding]:
    found: list[Finding] = []
    owners: dict[str, str] = {}
    for item in classes:
        try:
            token = class_token(item.class_id)
            if class_id_from_token(token) != item.class_id:
                raise TokenError(f"{token} decodes differently")
        except (TokenError, ValueError) as problem:
            found.append(error("token-roundtrip", item.class_id, str(problem)))
            continue
        if len(token.encode("ascii")) > max_bytes:
            found.append(error("token-overlong", item.class_id, f"{token} > {max_bytes} bytes"))
        if token in owners:
            found.append(error("token-collision", item.class_id, f"shares {owners[token]}"))
        owners.setdefault(token, item.class_id)
    return found


def validate_classes(classes: Sequence[SchemeClass], policy: SchemePolicy) -> list[Finding]:
    """Return every structural finding for a candidate class list."""
    counts = Counter(item.class_id for item in classes)
    found = [
        error("duplicate-class", class_id, f"appears {count} times")
        for class_id, count in sorted(counts.items())
        if count > 1
    ]
    for item in classes:
        found.extend(_namespace_findings(item))
        if item.namespace == NAMESPACE_OUTCOME:
            continue
        languages = {code for code, _ in item.captions}
        found.extend(
            error("missing-caption", item.class_id, f"no {language} caption")
            for language in policy.required_caption_languages
            if language not in languages
        )
        if item.parent_id is not None and item.parent_id not in counts:
            found.append(error("orphan-parent", item.class_id, f"parent {item.parent_id} absent"))
    found.extend(_cycle_findings(classes))
    found.extend(_token_findings(classes, policy.max_token_bytes))
    return found


def validate_licence(label: str, licence: Licence) -> list[Finding]:
    """Refuse a taxonomy or source without a licence name and URL."""
    if licence.name.strip() and licence.url.strip():
        return []
    return [error("missing-licence", None, f"{label} has no licence name and URL")]

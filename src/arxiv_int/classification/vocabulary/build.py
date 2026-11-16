"""Build frozen, content-addressed scheme rows from the committed taxonomy, extensions and outcomes."""

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from arxiv_int.classification.vocabulary.codes import CodeError, kind_for, parent_code
from arxiv_int.classification.vocabulary.coverage import balance, coverage
from arxiv_int.classification.vocabulary.model import (
    ANCESTOR_SEPARATOR,
    Scheme,
    SchemeClass,
    caption_pairs,
)
from arxiv_int.classification.vocabulary.outcomes import (
    EXCEPTIONAL_OUTCOMES,
    NAMESPACE_EXTENSION,
    NAMESPACE_OUTCOME,
    NAMESPACE_TAXONOMY,
    taxonomy_class_id,
)
from arxiv_int.classification.vocabulary.policy import Licence, SchemePolicy
from arxiv_int.classification.vocabulary.tokens import ascii_slug, class_token
from arxiv_int.classification.vocabulary.validate import (
    Finding,
    errors,
    validate_classes,
    validate_licence,
)

BUILDER_VERSION = "2"
CONTRACT_VERSION = "1.0.0"
SCHEME_PREFIX = "subjects"
KIND_EXTENSION = "extension"
KIND_OUTCOME = "outcome"
KIND_INVALID = "invalid"
SCHEME_COLUMNS = (
    "scheme_class_id",
    "scheme_id",
    "scheme_version",
    "generation_id",
    "contract_version",
)


def scheme_class_id(scheme_id: str, class_id: str) -> str:
    """Return the single-column row key ``<scheme id>:<class id>``."""
    return f"{scheme_id}:{class_id}"


@dataclass(frozen=True, slots=True)
class BuiltScheme:
    """Rows plus manifest when publishable, and every validation finding."""

    scheme_id: str
    rows: tuple[dict[str, Any], ...]
    manifest: dict[str, Any]
    findings: tuple[Finding, ...]

    @property
    def publishable(self) -> bool:
        return not errors(self.findings)


def _kind_and_parent(code: str) -> tuple[str, str | None]:
    try:
        parent = parent_code(code)
        return kind_for(code), taxonomy_class_id(parent) if parent else None
    except CodeError:
        return KIND_INVALID, None


def taxonomy_classes(policy: SchemePolicy) -> list[SchemeClass]:
    """Turn authored taxonomy entries into classes whose parents follow their codes."""
    items = []
    for entry in policy.taxonomy.entries:
        kind, parent = _kind_and_parent(entry.code)
        items.append(
            SchemeClass(
                taxonomy_class_id(entry.code),
                NAMESPACE_TAXONOMY,
                entry.code,
                parent,
                kind,
                entry.captions,
                entry.crosswalk,
            )
        )
    return items


def project_classes(policy: SchemePolicy) -> list[SchemeClass]:
    """Return operator-local extensions and the two outcome classes."""
    items = [
        SchemeClass(
            ext.class_id, NAMESPACE_EXTENSION, None, ext.parent_id, KIND_EXTENSION, ext.captions
        )
        for ext in policy.extensions
    ]
    for outcome in sorted(EXCEPTIONAL_OUTCOMES):
        captions = caption_pairs({"en": outcome.capitalize()})
        items.append(SchemeClass(outcome, NAMESPACE_OUTCOME, None, None, KIND_OUTCOME, captions))
    return items


def _row(scheme: Scheme, item: SchemeClass, policy: SchemePolicy) -> dict[str, Any]:
    captions = dict(item.captions)
    return {
        "ancestor_path": ANCESTOR_SEPARATOR.join(scheme.ancestors(item.class_id)),
        "caption_en": captions.get("en"),
        "caption_ru": captions.get("ru"),
        "caption_uk": captions.get("uk"),
        "captions_json": json.dumps(captions, sort_keys=True, ensure_ascii=True),
        "class_id": item.class_id,
        "class_kind": item.kind,
        "code": item.code,
        "crosswalk_json": json.dumps(list(item.crosswalk), ensure_ascii=True),
        "depth": scheme.depth(item.class_id),
        "namespace": item.namespace,
        "parent_class_id": item.parent_id,
        "path_token": class_token(item.class_id),
        "slug": ascii_slug(captions.get("en", ""), policy.max_slug_bytes),
    }


def content_sha256(rows: Sequence[Mapping[str, Any]]) -> str:
    """Hash the scheme-independent columns of rows in order."""
    digest = hashlib.sha256()
    for row in rows:
        identity = {key: value for key, value in row.items() if key not in SCHEME_COLUMNS}
        digest.update(json.dumps(identity, sort_keys=True, ensure_ascii=True).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _licence(licence: Licence) -> dict[str, str]:
    return {"name": licence.name, "url": licence.url}


def _manifest(
    policy: SchemePolicy, rows: Sequence[Mapping[str, Any]], stats: Mapping[str, Any]
) -> dict[str, Any]:
    taxonomy = policy.taxonomy
    return {
        **stats,
        "builderVersion": BUILDER_VERSION,
        "captionLanguages": list(policy.caption_languages),
        "contractVersion": CONTRACT_VERSION,
        "counts": {
            "byKind": dict(sorted(Counter(str(row["class_kind"]) for row in rows).items())),
            "byNamespace": dict(sorted(Counter(str(row["namespace"]) for row in rows).items())),
            "classes": len(rows),
        },
        "extensions": {
            "count": len(policy.extensions),
            "sha256": policy.extensions_sha256,
            "version": policy.extensions_version,
        },
        "outcomes": dict(sorted(policy.outcomes.items())),
        "policy": {"sha256": policy.policy_sha256, "version": policy.policy_version},
        "primaryKinds": sorted(policy.primary_kinds),
        "sources": [
            {
                "licence": _licence(source.licence),
                "publisher": source.publisher,
                "retrievedAt": source.retrieved_at,
                "sha256": source.sha256,
                "sourceId": source.source_id,
                "url": source.url,
            }
            for source in policy.sources
        ],
        "taxonomy": {
            "copyright": taxonomy.copyright,
            "licence": _licence(taxonomy.licence),
            "sha256": taxonomy.sha256,
            "taxonomyId": taxonomy.taxonomy_id,
            "title": taxonomy.title,
            "version": taxonomy.version,
        },
    }


def _licence_findings(policy: SchemePolicy) -> list[Finding]:
    found = validate_licence(policy.taxonomy.taxonomy_id, policy.taxonomy.licence)
    for source in policy.sources:
        found.extend(validate_licence(source.source_id, source.licence))
    return found


def build_scheme(policy: SchemePolicy, *, run_id: str) -> BuiltScheme:
    """Validate and freeze the scheme; rows are empty when a blocking finding exists."""
    classes = [*taxonomy_classes(policy), *project_classes(policy)]
    findings = [*validate_classes(classes, policy), *_licence_findings(policy)]
    coverage_findings, coverage_stats = coverage(classes, policy.sources)
    findings.extend(coverage_findings)
    if errors(findings):
        return BuiltScheme("", (), {}, tuple(findings))
    scheme = Scheme.of(classes)
    balance_findings, balance_stats = balance(scheme, policy.balance)
    findings.extend(balance_findings)
    if errors(findings):
        return BuiltScheme("", (), {}, tuple(findings))
    rows = [_row(scheme, item, policy) for item in classes]
    digest = content_sha256(rows)
    scheme_id = f"{SCHEME_PREFIX}-{digest[:12]}"
    version = f"{policy.taxonomy.version}+{digest[:12]}"
    for row in rows:
        row.update(
            scheme_class_id=scheme_class_id(scheme_id, str(row["class_id"])),
            scheme_id=scheme_id,
            scheme_version=version,
            generation_id=run_id,
            contract_version=CONTRACT_VERSION,
        )
    manifest = _manifest(policy, rows, {"balance": balance_stats, "coverage": coverage_stats})
    manifest.update(contentSha256=digest, runId=run_id, schemeId=scheme_id, schemeVersion=version)
    return BuiltScheme(scheme_id, tuple(rows), manifest, tuple(findings))

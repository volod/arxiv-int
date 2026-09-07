"""Stable entity and field substitutions with collision refusal."""

from dataclasses import dataclass

from arxiv_int.evaluation.export_catalog import CatalogEntity, CatalogField, IdentityCatalog
from arxiv_int.evaluation.export_errors import ExportCollisionError, ExportSpanError
from arxiv_int.evaluation.export_normalize import digit_string, normalize_email, normalize_phone
from arxiv_int.evaluation.export_render import (
    account_substitute,
    address_substitutes,
    email_substitute,
    entity_label,
    phone_substitute,
)

MIN_GLOBAL_NEEDLE = 3
MIN_DIGIT_NEEDLE = 7
STRUCTURED_KEYS = frozenset(
    {"account", "address", "city", "country", "email", "house", "phone", "postal", "street"}
)


def surface_forms(entity: CatalogEntity) -> tuple[str, ...]:
    """Return unique labels, aliases, and the stable entity id."""
    return tuple(dict.fromkeys((*entity.labels, *entity.aliases, entity.entity_id)))


@dataclass(frozen=True, slots=True)
class AppliedSpan:
    """A catalog span bound to a concrete substitute."""

    artifact: str
    start: int
    end: int
    original: str
    substitute: str
    entity_id: str


@dataclass(frozen=True, slots=True)
class SubstitutionTable:
    """Complete source-to-substitute map plus rewrite indexes."""

    entity_labels: dict[str, str]
    entity_surfaces: dict[str, tuple[str, ...]]
    replacements: tuple[tuple[str, str], ...]
    structured: dict[str, str]
    ambiguous: frozenset[str]
    spans: tuple[AppliedSpan, ...]
    needles: tuple[str, ...]
    reference_map: dict[str, dict[str, str]]


def build_substitution_table(
    catalog: IdentityCatalog, artifact_texts: dict[str, str]
) -> SubstitutionTable:
    """Build deterministic substitutions and refuse colliding outputs."""
    claims: dict[str, str] = {}
    entity_labels: dict[str, str] = {}
    entity_surfaces: dict[str, tuple[str, ...]] = {}
    surfaces: dict[str, set[str]] = {}
    aliases: dict[str, str] = {}
    for entity in catalog.entities:
        substitute = _claim(claims, f"entity:{entity.entity_id}", entity_label(entity))
        entity_labels[entity.entity_id] = substitute
        entity_surfaces[entity.entity_id] = surface_forms(entity)
        for surface in entity_surfaces[entity.entity_id]:
            surfaces.setdefault(surface, set()).add(entity.entity_id)
            if surface != entity.entity_id:
                aliases[surface] = substitute
    unambiguous: dict[str, str] = {}
    ambiguous: set[str] = set()
    for surface, owners in surfaces.items():
        if len(owners) == 1:
            unambiguous[surface] = entity_labels[next(iter(owners))]
        else:
            ambiguous.add(surface)
    field_map = _field_replacements(catalog.fields, claims)
    structured = dict(field_map)
    for original, substitute in field_map.items():
        if original not in ambiguous and not skip_global_needle(original):
            unambiguous[original] = substitute
    replacements = tuple(sorted(unambiguous.items(), key=lambda item: (-len(item[0]), item[0])))
    spans = _bind_spans(catalog, entity_labels, artifact_texts)
    return SubstitutionTable(
        entity_labels,
        entity_surfaces,
        replacements,
        structured,
        frozenset(ambiguous),
        spans,
        _needles(catalog, field_map),
        {"aliases": aliases, "entities": dict(entity_labels), "fields": dict(field_map)},
    )


def skip_global_needle(original: str) -> bool:
    """Return True when a value is too short to replace globally."""
    digits = digit_string(original)
    if digits == original and len(digits) < MIN_DIGIT_NEEDLE:
        return True
    return len(original) < MIN_GLOBAL_NEEDLE


def _field_replacements(fields: tuple[CatalogField, ...], claims: dict[str, str]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for field in fields:
        canonical = f"field:{field.kind}:{field.value}"
        for original, substitute in _render_field(field).items():
            mapping[original] = _claim(claims, canonical, substitute)
    return mapping


def _render_field(field: CatalogField) -> dict[str, str]:
    if field.kind == "email":
        substitute = email_substitute(field.value)
        return {field.value: substitute, normalize_email(field.value): substitute}
    if field.kind == "phone":
        substitute = phone_substitute(field)
        originals = {field.value, normalize_phone(field.value), digit_string(field.value)}
        return {item: substitute for item in originals if item}
    if field.kind == "account":
        substitute = account_substitute(field)
        originals = {field.value, field.value.replace(" ", ""), digit_string(field.value)}
        return {item: substitute for item in originals if item}
    return address_substitutes(field)


def _bind_spans(
    catalog: IdentityCatalog,
    entity_labels: dict[str, str],
    artifact_texts: dict[str, str],
) -> tuple[AppliedSpan, ...]:
    bound: list[AppliedSpan] = []
    for span in catalog.spans:
        text = artifact_texts.get(span.artifact)
        if text is None:
            continue
        original = text[span.start : span.end]
        entity = catalog.entity_by_id[span.entity_id]
        if original not in surface_forms(entity):
            raise ExportSpanError(
                f"span {span.artifact}[{span.start}:{span.end}] does not match entity surfaces"
            )
        bound.append(
            AppliedSpan(
                span.artifact,
                span.start,
                span.end,
                original,
                entity_labels[span.entity_id],
                span.entity_id,
            )
        )
    _refuse_overlap(bound)
    return tuple(bound)


def _refuse_overlap(spans: list[AppliedSpan]) -> None:
    ordered = sorted(spans, key=lambda item: (item.artifact, item.start, item.end))
    previous: AppliedSpan | None = None
    for span in ordered:
        overlapping = (
            previous is not None
            and span.artifact == previous.artifact
            and span.start < previous.end
        )
        if overlapping:
            raise ExportSpanError(f"overlapping identity spans on {span.artifact}")
        previous = span


def _needles(catalog: IdentityCatalog, field_map: dict[str, str]) -> tuple[str, ...]:
    needles: list[str] = []
    for entity in catalog.entities:
        needles.extend(surface_forms(entity))
    needles.extend(original for original in field_map if not skip_global_needle(original))
    unique = list(dict.fromkeys(item for item in needles if item))
    unique.sort(key=lambda item: (-len(item), item))
    return tuple(unique)


def _claim(claims: dict[str, str], canonical: str, substitute: str) -> str:
    prior = claims.get(substitute)
    if prior is not None and prior != canonical:
        raise ExportCollisionError("identity substitution collided")
    claims[substitute] = canonical
    return substitute

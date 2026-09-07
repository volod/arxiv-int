"""Source identity catalog loaded from a verified run bundle."""

from collections.abc import Mapping
from dataclasses import dataclass

from arxiv_int.evaluation.bundle_errors import BundleManifestError
from arxiv_int.evaluation.bundle_manifest import identity_text
from arxiv_int.evaluation.export_errors import ExportCatalogError
from arxiv_int.evaluation.export_policy import (
    ACCOUNT_SCHEMES,
    ENTITY_KINDS,
    FIELD_KINDS,
    IDENTITIES_ARTIFACT,
)

CATALOG_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class CatalogEntity:
    """One person, company, or product with stable id and surface forms."""

    entity_id: str
    kind: str
    labels: tuple[str, ...]
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CatalogField:
    """One typed contact, address, or account value."""

    kind: str
    value: str
    scheme: str
    prefix: str
    street: str
    house: str
    city: str
    postal: str
    country: str


@dataclass(frozen=True, slots=True)
class CatalogSpan:
    """One character span that binds a surface form to an entity."""

    artifact: str
    start: int
    end: int
    entity_id: str


@dataclass(frozen=True, slots=True)
class IdentityCatalog:
    """Declared identities that must be rewritten together."""

    entities: tuple[CatalogEntity, ...]
    fields: tuple[CatalogField, ...]
    spans: tuple[CatalogSpan, ...]

    @property
    def entity_by_id(self) -> dict[str, CatalogEntity]:
        return {entity.entity_id: entity for entity in self.entities}


def empty_catalog() -> IdentityCatalog:
    """Return a catalog for synthetic fixtures with no real identities."""
    return IdentityCatalog((), (), ())


def parse_identity_catalog(payload: object) -> IdentityCatalog:
    """Parse `identities.json` or raise a typed catalog failure."""
    if not isinstance(payload, dict):
        raise ExportCatalogError(f"{IDENTITIES_ARTIFACT} is not an object")
    extra = sorted(set(payload) - {"schema_version", "entities", "fields", "spans"})
    if extra or payload.get("schema_version") != CATALOG_SCHEMA_VERSION:
        raise ExportCatalogError(f"{IDENTITIES_ARTIFACT} identities are missing or malformed")
    entities = _entities(payload.get("entities", []))
    fields = _fields(payload.get("fields", []))
    spans = _spans(payload.get("spans", []), {entity.entity_id for entity in entities})
    return IdentityCatalog(entities, fields, spans)


def catalog_as_json(catalog: IdentityCatalog) -> dict[str, object]:
    """Return a canonical identity-catalog object for local diagnostics."""
    return {
        "entities": [_entity_json(entity) for entity in catalog.entities],
        "fields": [_field_json(field) for field in catalog.fields],
        "schema_version": CATALOG_SCHEMA_VERSION,
        "spans": [_span_json(span) for span in catalog.spans],
    }


def _entities(value: object) -> tuple[CatalogEntity, ...]:
    if not isinstance(value, list):
        raise ExportCatalogError("identities entities must be an array")
    entities: list[CatalogEntity] = []
    seen: set[str] = set()
    for item in value:
        entity = _entity(item)
        if entity.entity_id in seen:
            raise ExportCatalogError(f"duplicate identity entity id: {entity.entity_id}")
        seen.add(entity.entity_id)
        entities.append(entity)
    entities.sort(key=lambda item: (item.kind, item.entity_id))
    return tuple(entities)


def _entity(item: object) -> CatalogEntity:
    if not isinstance(item, dict):
        raise ExportCatalogError("identity entity must be an object")
    entity_id = _identity("entity id", item.get("id"))
    kind = _identity("entity kind", item.get("kind"))
    if kind not in ENTITY_KINDS:
        raise ExportCatalogError(f"unsupported identity entity kind: {kind}")
    labels = _string_list("labels", item.get("labels", []))
    aliases = _string_list("aliases", item.get("aliases", []))
    if not labels:
        raise ExportCatalogError(f"identity entity {entity_id} has no labels")
    return CatalogEntity(entity_id, kind, labels, aliases)


def _fields(value: object) -> tuple[CatalogField, ...]:
    if not isinstance(value, list):
        raise ExportCatalogError("identities fields must be an array")
    fields = [_field(item) for item in value]
    fields.sort(key=lambda item: (item.kind, item.scheme, item.value))
    return tuple(fields)


def _field(item: object) -> CatalogField:
    if not isinstance(item, dict):
        raise ExportCatalogError("identity field must be an object")
    kind = _identity("field kind", item.get("kind"))
    if kind not in FIELD_KINDS:
        raise ExportCatalogError(f"unsupported identity field kind: {kind}")
    scheme = str(item.get("scheme") or _default_scheme(kind, item))
    if kind == "account" and scheme not in ACCOUNT_SCHEMES:
        raise ExportCatalogError(f"unsupported account scheme: {scheme}")
    prefix = _optional_text("prefix", item.get("prefix", ""))
    street = _optional_text("street", item.get("street", ""))
    house = _optional_text("house", item.get("house", ""))
    city = _optional_text("city", item.get("city", ""))
    postal = _optional_text("postal", item.get("postal", ""))
    country = _optional_text("country", item.get("country", ""))
    value = _optional_text("value", item.get("value", "")) or _address_value(
        street, house, city, postal, country
    )
    if not value:
        raise ExportCatalogError(f"identity {kind} field has no value")
    return CatalogField(kind, value, scheme, prefix, street, house, city, postal, country)


def _spans(value: object, entity_ids: set[str]) -> tuple[CatalogSpan, ...]:
    if not isinstance(value, list):
        raise ExportCatalogError("identities spans must be an array")
    spans = [_span(item, entity_ids) for item in value]
    spans.sort(key=lambda item: (item.artifact, item.start, item.end, item.entity_id))
    return tuple(spans)


def _span(item: object, entity_ids: set[str]) -> CatalogSpan:
    if not isinstance(item, dict):
        raise ExportCatalogError("identity span must be an object")
    artifact = _identity("span artifact", item.get("artifact"))
    start = item.get("start")
    end = item.get("end")
    if isinstance(start, bool) or not isinstance(start, int) or start < 0:
        raise ExportCatalogError("identity span start is malformed")
    if isinstance(end, bool) or not isinstance(end, int) or end < start:
        raise ExportCatalogError("identity span end is malformed")
    entity_id = _identity("span entity id", item.get("entity_id"))
    if entity_id not in entity_ids:
        raise ExportCatalogError(f"identity span refers to unknown entity: {entity_id}")
    return CatalogSpan(artifact, start, end, entity_id)


def _string_list(field: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ExportCatalogError(f"identity {field} must be an array")
    items = [_identity(field, item) for item in value]
    return tuple(dict.fromkeys(items))


def _optional_text(field: str, value: object) -> str:
    if value in (None, ""):
        return ""
    return _identity(field, value)


def _default_scheme(kind: str, item: Mapping[str, object]) -> str:
    if kind != "account":
        return ""
    raw = str(item.get("value") or "")
    compact = raw.replace(" ", "").upper()
    if len(compact) >= 4 and compact[:2].isalpha() and compact[2:4].isdigit():
        return "iban"
    digits = "".join(char for char in compact if char.isdigit())
    if digits == compact and len(digits) == 10:
        return "inn10"
    if digits == compact and len(digits) == 12:
        return "inn12"
    if digits == compact and 13 <= len(digits) <= 19:
        return "luhn"
    return "digits"


def _address_value(street: str, house: str, city: str, postal: str, country: str) -> str:
    parts = [part for part in (f"{street} {house}".strip(), city, postal, country) if part]
    return ", ".join(parts)


def _entity_json(entity: CatalogEntity) -> dict[str, object]:
    return {
        "aliases": list(entity.aliases),
        "id": entity.entity_id,
        "kind": entity.kind,
        "labels": list(entity.labels),
    }


def _field_json(field: CatalogField) -> dict[str, object]:
    payload: dict[str, object] = {"kind": field.kind, "value": field.value}
    for key in ("scheme", "prefix", "street", "house", "city", "postal", "country"):
        item = getattr(field, key)
        if item:
            payload[key] = item
    return payload


def _span_json(span: CatalogSpan) -> dict[str, object]:
    return {
        "artifact": span.artifact,
        "end": span.end,
        "entity_id": span.entity_id,
        "start": span.start,
    }


def _identity(field: str, value: object) -> str:
    try:
        return identity_text(field, value)
    except BundleManifestError as error:
        raise ExportCatalogError(str(error)) from error

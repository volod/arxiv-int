"""Entity, fact, and catalog fixture families."""

from arxiv_int.evaluation.fixtures.build import family, item, pair_splits
from arxiv_int.evaluation.fixtures.kinds import (
    KIND_CATALOG,
    KIND_ENTITY,
    KIND_FACT,
    SPLIT_FINAL,
    SPLIT_TUNING,
)
from arxiv_int.evaluation.fixtures.model import GoldFamily


def entity_family() -> GoldFamily:
    """Match/non-match pairs including same-name nonmatches."""
    match = {
        "left_id": "person:alpha",
        "match": True,
        "right_id": "person:alpha-alias",
        "same_name": False,
    }
    same_name = {
        "left_id": "person:alpha",
        "match": False,
        "right_id": "person:gamma",
        "same_name": True,
    }
    tuning, final = pair_splits(
        item_kind=KIND_ENTITY,
        stem="entity-match",
        gold=match,
        positive={"predicted_matches": [["person:alpha", "person:alpha-alias"]], "threshold": 0.9},
        negative={"predicted_matches": [["person:alpha", "person:gamma"]], "threshold": 0.9},
        source="fixture://identity/pairs.json",
        evidence="pair:alpha-alias",
        label="person:alpha",
        extra_gold={**match, "left_id": "person:beta", "right_id": "person:beta-alias"},
        extra_positive={
            "predicted_matches": [["person:beta", "person:beta-alias"]],
            "threshold": 0.9,
        },
    )
    nonmatch = item(
        item_id="entity-same-name-final",
        item_kind=KIND_ENTITY,
        split=SPLIT_FINAL,
        gold_ref="gold:entity-same-name:final",
        gold=same_name,
        positive={"predicted_matches": [], "threshold": 0.9},
        negative={"predicted_matches": [["person:alpha", "person:gamma"]], "threshold": 0.9},
        source="fixture://identity/same-name.json",
        evidence="pair:alpha-gamma",
        label="Fixture Person",
        extra_provenance={"same_name": "true"},
    )
    return family(KIND_ENTITY, (tuning, final, nonmatch))


def fact_family() -> GoldFamily:
    """Typed facts with citation spans and invalid structured output."""
    gold = {
        "object_id": "product:pump",
        "predicate": "pred.manufactures",
        "span": {"document_id": "fact-1", "end": 18, "start": 0},
        "subject_id": "company:acme",
        "valid": True,
    }
    tuning, final = pair_splits(
        item_kind=KIND_FACT,
        stem="fact-manufactures",
        gold=gold,
        positive=gold,
        negative={**gold, "object_id": "product:other", "valid": False},
        source="fixture://facts/manufactures.txt",
        evidence="span:fact-1:0:18",
        query_text="who manufactures the pump",
        extra_gold={**gold, "object_id": "product:valve", "subject_id": "company:beta"},
    )
    invalid = item(
        item_id="fact-invalid-json-final",
        item_kind=KIND_FACT,
        split=SPLIT_FINAL,
        gold_ref="gold:fact-invalid:final",
        gold={**gold, "valid": False, "failure": "schema"},
        positive={"failure": "schema", "valid": False},
        negative={**gold, "valid": True},
        source="fixture://facts/invalid.txt",
        evidence="extractor:schema-reject",
        query_text="reject malformed structured output",
    )
    return family(KIND_FACT, (tuning, final, invalid))


def catalog_family() -> GoldFamily:
    """Company, product, and person rows with merge, split, and removal."""
    company = {
        "aliases": ["Fixture Co"],
        "catalog": "company",
        "entity_id": "company:acme",
        "label": "Fixture Company LLC",
        "roles": ["supplier"],
    }
    person = {
        "aliases": ["F. Person"],
        "catalog": "person",
        "entity_id": "person:alpha",
        "label": "Fixture Person Alpha",
        "roles": ["employee"],
    }
    removed = {
        "aliases": [],
        "catalog": "product",
        "entity_id": "product:retired",
        "label": "Retired Pump",
        "roles": [],
        "status": "removed",
    }
    tuning, final = pair_splits(
        item_kind=KIND_CATALOG,
        stem="catalog-company",
        gold=company,
        positive=company,
        negative={**company, "entity_id": "company:other", "label": "Other Co"},
        source="fixture://catalogs/company.json",
        evidence="identity:company:acme",
        label="Fixture Company LLC",
        extra_gold={**company, "entity_id": "company:beta", "label": "Fixture Company Beta"},
    )
    person_item = item(
        item_id="catalog-person-final",
        item_kind=KIND_CATALOG,
        split=SPLIT_FINAL,
        gold_ref="gold:catalog-person:final",
        gold=person,
        positive=person,
        negative={**person, "entity_id": "person:gamma", "label": "Fixture Person Alpha"},
        source="fixture://catalogs/person.json",
        evidence="identity:person:alpha",
        label="Fixture Person Alpha",
        extra_provenance={"same_name_nonmatch": "person:gamma"},
    )
    removal = item(
        item_id="catalog-product-removed-tuning",
        item_kind=KIND_CATALOG,
        split=SPLIT_TUNING,
        gold_ref="gold:catalog-removed:tuning",
        gold=removed,
        positive=removed,
        negative={**removed, "status": "active"},
        source="fixture://catalogs/product.json",
        evidence="identity:product:retired",
        label="Retired Pump",
    )
    return family(KIND_CATALOG, (tuning, final, person_item, removal))

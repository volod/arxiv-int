"""Ontology, geotemporal, and graph fixture families."""

from arxiv_int.evaluation.fixture_build import family, item, pair_splits
from arxiv_int.evaluation.fixture_kinds import (
    KIND_GEOTEMPORAL,
    KIND_GRAPH,
    KIND_ONTOLOGY,
    SPLIT_FINAL,
    SPLIT_TUNING,
)
from arxiv_int.evaluation.fixture_model import GoldFamily


def ontology_family() -> GoldFamily:
    """Additive add, deprecate-with-successor, draft refusal, and contradiction."""
    add_gold = {"action": "add", "change": "additive", "term_id": "pred.fixture-new"}
    deprecate_gold = {
        "action": "deprecate",
        "change": "additive",
        "successor": "pred.fixture-next",
        "term_id": "pred.fixture-old",
    }
    draft_gold = {"action": "draft", "allowed": False, "term_id": "pred.fixture-draft"}
    contradiction = {
        "action": "contradiction",
        "allowed": False,
        "types": ["class.natural-person", "class.legal-entity"],
    }
    add_item = item(
        item_id="ontology-add-tuning",
        item_kind=KIND_ONTOLOGY,
        split=SPLIT_TUNING,
        gold_ref="gold:ontology-add:tuning",
        gold=add_gold,
        positive=add_gold,
        negative={**add_gold, "change": "breaking"},
        source="fixture://ontology/add.json",
        evidence="evolution:add:pred.fixture-new",
    )
    deprecate_item = item(
        item_id="ontology-deprecate-final",
        item_kind=KIND_ONTOLOGY,
        split=SPLIT_FINAL,
        gold_ref="gold:ontology-deprecate:final",
        gold=deprecate_gold,
        positive=deprecate_gold,
        negative={**deprecate_gold, "successor": None, "change": "breaking"},
        source="fixture://ontology/deprecate.json",
        evidence="evolution:deprecate:pred.fixture-old",
    )
    draft_item = item(
        item_id="ontology-draft-tuning",
        item_kind=KIND_ONTOLOGY,
        split=SPLIT_TUNING,
        gold_ref="gold:ontology-draft:tuning",
        gold=draft_gold,
        positive=draft_gold,
        negative={**draft_gold, "allowed": True},
        source="fixture://ontology/draft.json",
        evidence="evolution:draft:pred.fixture-draft",
    )
    conflict = item(
        item_id="ontology-contradiction-final",
        item_kind=KIND_ONTOLOGY,
        split=SPLIT_FINAL,
        gold_ref="gold:ontology-contradiction:final",
        gold=contradiction,
        positive=contradiction,
        negative={**contradiction, "allowed": True},
        source="fixture://ontology/contradiction.json",
        evidence="disjoint:person-legal",
    )
    return family(KIND_ONTOLOGY, (add_item, deprecate_item, draft_item, conflict))


def geotemporal_family() -> GoldFamily:
    """Source-valid vs recorded time, CRS uncertainty, roles, and effectivity."""
    valid_time = {
        "crs": "EPSG:4326",
        "latitude": 55.75,
        "longitude": 37.62,
        "recorded_time": "2021-06-01",
        "role_end": "2020-12-31",
        "role_start": "2018-01-01",
        "source_valid_end": "2020-01-01",
        "source_valid_start": "2019-01-01",
        "unknown_crs": False,
    }
    unknown = {
        "crs": None,
        "latitude": None,
        "longitude": None,
        "place": "ambiguous-station",
        "recorded_time": "2021-06-01",
        "source_valid_start": "2019",
        "unknown_crs": True,
    }
    effectivity = {
        "as_of": "2020-07-01",
        "product_id": "product:pump",
        "revision": "B",
        "revision_a_end": "2020-06-30",
        "revision_b_start": "2020-07-01",
    }
    time_item = item(
        item_id="geo-valid-vs-recorded-tuning",
        item_kind=KIND_GEOTEMPORAL,
        split=SPLIT_TUNING,
        gold_ref="gold:geo-time:tuning",
        gold=valid_time,
        positive=valid_time,
        negative={**valid_time, "source_valid_start": "2021-06-01", "recorded_time": "2021-06-01"},
        source="fixture://geo/role.json",
        evidence="valid-time:2019/2020",
        extra_provenance={"as_of": "2019-06-01"},
    )
    crs_item = item(
        item_id="geo-unknown-crs-final",
        item_kind=KIND_GEOTEMPORAL,
        split=SPLIT_FINAL,
        gold_ref="gold:geo-crs:final",
        gold=unknown,
        positive=unknown,
        negative={
            **unknown,
            "crs": "EPSG:4326",
            "latitude": 0.0,
            "longitude": 0.0,
            "unknown_crs": False,
        },
        source="fixture://geo/place.json",
        evidence="place:ambiguous-station",
    )
    rev_item = item(
        item_id="geo-effectivity-final",
        item_kind=KIND_GEOTEMPORAL,
        split=SPLIT_FINAL,
        gold_ref="gold:geo-effectivity:final",
        gold=effectivity,
        positive=effectivity,
        negative={**effectivity, "revision": "A"},
        source="fixture://geo/revision.json",
        evidence="effectivity:product:pump:B",
    )
    role_item = item(
        item_id="geo-role-interval-tuning",
        item_kind=KIND_GEOTEMPORAL,
        split=SPLIT_TUNING,
        gold_ref="gold:geo-role:tuning",
        gold={**valid_time, "as_of": "2021-06-01", "role_active": False},
        positive={**valid_time, "as_of": "2021-06-01", "role_active": False},
        negative={**valid_time, "as_of": "2021-06-01", "role_active": True},
        source="fixture://geo/role.json",
        evidence="role-interval:2018/2020",
    )
    return family(KIND_GEOTEMPORAL, (time_item, crs_item, rev_item, role_item))


def graph_family() -> GoldFamily:
    """Graph path answers that must match relational SQL."""
    gold = {
        "path": ["company:acme", "product:pump"],
        "predicate": "pred.manufactures",
        "sql_rows": [["company:acme", "product:pump"]],
    }
    tuning, final = pair_splits(
        item_kind=KIND_GRAPH,
        stem="graph-manufactures",
        gold=gold,
        positive=gold,
        negative={"path": ["company:acme", "person:alpha"], "sql_rows": gold["sql_rows"]},
        source="fixture://graph/manufactures.json",
        evidence="sql:fact.manufactures",
        extra_gold={
            "path": ["company:beta", "product:valve"],
            "predicate": "pred.manufactures",
            "sql_rows": [["company:beta", "product:valve"]],
        },
    )
    return family(KIND_GRAPH, (tuning, final))

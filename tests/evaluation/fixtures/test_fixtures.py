import pytest

from arxiv_int.evaluation.evaluate.errors import MissingEvidenceError, SplitLeakError
from arxiv_int.evaluation.families import all_items, built_families, catalog_document
from arxiv_int.evaluation.fixtures.guard import (
    detect_split_leakage,
    item_ledger,
    refuse_split_leakage,
)
from arxiv_int.evaluation.fixtures.kinds import DEFAULT_BOOTSTRAP_SEED, SPLIT_FINAL, SPLIT_TUNING
from arxiv_int.evaluation.fixtures.model import item_from_payload
from arxiv_int.evaluation.scoring import polarity_scores, score_item


def test_frozen_families_cover_required_kinds_and_splits() -> None:
    families = built_families()
    kinds = {family.family for family in families}
    items = all_items(families)
    splits = {item.split for item in items}
    assert kinds == {
        "anomaly",
        "catalog",
        "classification",
        "domain-artifact",
        "domain-negative",
        "entity",
        "extraction",
        "fact",
        "geotemporal",
        "graph",
        "ontology",
        "reporting",
        "russian-retrieval",
        "semantic",
    }
    assert splits == {SPLIT_TUNING, SPLIT_FINAL}
    assert all(item.gold_ref and item.provenance["source"] for item in items)
    ledger = item_ledger(items)
    assert ledger.seed == DEFAULT_BOOTSTRAP_SEED
    assert catalog_document(families)["ledger_fingerprint"] == ledger.fingerprint
    assert item_ledger(items, seed=DEFAULT_BOOTSTRAP_SEED) == ledger


def test_split_leakage_refuses_shared_identity_and_gold() -> None:
    items = list(all_items())
    leaked = item_from_payload(
        {
            **next(item.as_json_dict() for item in items if item.split == SPLIT_TUNING),
            "item_id": "leaked-final",
            "split": SPLIT_FINAL,
        }
    )
    findings = detect_split_leakage((*items, leaked))
    assert findings
    with pytest.raises(SplitLeakError):
        refuse_split_leakage((*items, leaked))


def test_positive_fixtures_beat_negative_fixtures() -> None:
    for item in all_items():
        positive, negative = polarity_scores(item)
        assert positive > negative, item.item_id


def test_missing_prediction_refuses_a_verdict() -> None:
    item = all_items()[0]
    with pytest.raises(MissingEvidenceError, match="no prediction"):
        score_item(item, None)


def test_same_name_and_domain_negatives_stay_invalid() -> None:
    items = {item.item_id: item for item in all_items()}
    same_name = items["entity-same-name-final"]
    delivery = items["domain-invoice-not-delivery-tuning"]
    assert same_name.gold["match"] is False
    assert same_name.gold["same_name"] is True
    assert delivery.gold["valid"] is False
    assert polarity_scores(same_name)[0] > polarity_scores(same_name)[1]
    assert polarity_scores(delivery)[0] > polarity_scores(delivery)[1]

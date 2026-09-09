"""Domain-artifact, anomaly, and domain-non-implication fixture families."""

from arxiv_int.evaluation.fixtures.build import family, item, pair_splits
from arxiv_int.evaluation.fixtures.kinds import (
    KIND_ANOMALY,
    KIND_DOMAIN_ARTIFACT,
    KIND_DOMAIN_NEGATIVE,
    SPLIT_FINAL,
    SPLIT_TUNING,
)
from arxiv_int.evaluation.fixtures.model import GoldFamily


def domain_artifact_family() -> GoldFamily:
    """BOM arithmetic, invoice totals, supply-chain stages, and valid empty."""
    bom = {
        "child_id": "product:bolt",
        "parent_id": "product:pump",
        "quantity": 4.0,
        "total": 4.0,
        "unit": "ea",
    }
    invoice = {
        "allocated": 100.0,
        "amount": 100.0,
        "currency": "RUB",
        "invoice_id": "inv-1",
    }
    empty = {
        "artifact_type": "supply-chain",
        "creation_status": "empty",
        "failure_reason": None,
    }
    bom_pair = pair_splits(
        item_kind=KIND_DOMAIN_ARTIFACT,
        stem="domain-bom",
        gold=bom,
        positive=bom,
        negative={**bom, "total": 8.0},
        source="fixture://domain/bom.json",
        evidence="bom:pump:bolt",
        extra_gold={**bom, "child_id": "product:gasket", "quantity": 2.0, "total": 2.0},
    )
    invoice_item = item(
        item_id="domain-invoice-tuning",
        item_kind=KIND_DOMAIN_ARTIFACT,
        split=SPLIT_TUNING,
        gold_ref="gold:domain-invoice:tuning",
        gold=invoice,
        positive=invoice,
        negative={**invoice, "allocated": 150.0},
        source="fixture://domain/invoice.json",
        evidence="invoice:inv-1",
    )
    empty_item = item(
        item_id="domain-empty-final",
        item_kind=KIND_DOMAIN_ARTIFACT,
        split=SPLIT_FINAL,
        gold_ref="gold:domain-empty:final",
        gold=empty,
        positive=empty,
        negative={**empty, "creation_status": "failed", "failure_reason": "missing"},
        source="fixture://domain/supply.json",
        evidence="registry:supply-chain:empty",
    )
    return family(KIND_DOMAIN_ARTIFACT, (*bom_pair, invoice_item, empty_item))


def anomaly_family() -> GoldFamily:
    """Positives, hard negatives, insufficient cohorts, leakage, and review budget."""
    positive = {
        "cohort": "positive",
        "detector": "amount-mismatch",
        "flagged": True,
        "review_needed": True,
        "time_leakage": False,
    }
    hard_neg = {
        "cohort": "hard-negative",
        "detector": "amount-mismatch",
        "flagged": False,
        "review_needed": False,
        "time_leakage": False,
    }
    insufficient = {
        "cohort": "insufficient",
        "detector": "graph-cycle",
        "flagged": False,
        "insufficient": True,
        "review_needed": False,
    }
    leakage = {
        "cohort": "time-leakage",
        "detector": "drift",
        "flagged": False,
        "time_leakage": True,
        "valid": False,
    }
    pos_item = item(
        item_id="anomaly-positive-tuning",
        item_kind=KIND_ANOMALY,
        split=SPLIT_TUNING,
        gold_ref="gold:anomaly-positive:tuning",
        gold=positive,
        positive=positive,
        negative={**positive, "flagged": False, "review_needed": False},
        source="fixture://anomaly/positive.json",
        evidence="finding:amount-mismatch:1",
    )
    hard_item = item(
        item_id="anomaly-hard-negative-final",
        item_kind=KIND_ANOMALY,
        split=SPLIT_FINAL,
        gold_ref="gold:anomaly-hard-neg:final",
        gold=hard_neg,
        positive=hard_neg,
        negative={**hard_neg, "flagged": True, "review_needed": True},
        source="fixture://anomaly/hard-neg.json",
        evidence="finding:amount-mismatch:2",
    )
    short_item = item(
        item_id="anomaly-insufficient-tuning",
        item_kind=KIND_ANOMALY,
        split=SPLIT_TUNING,
        gold_ref="gold:anomaly-insufficient:tuning",
        gold=insufficient,
        positive=insufficient,
        negative={**insufficient, "flagged": True, "insufficient": False},
        source="fixture://anomaly/insufficient.json",
        evidence="finding:graph-cycle:skip",
    )
    leak_item = item(
        item_id="anomaly-time-leakage-final",
        item_kind=KIND_ANOMALY,
        split=SPLIT_FINAL,
        gold_ref="gold:anomaly-leakage:final",
        gold=leakage,
        positive=leakage,
        negative={**leakage, "flagged": True, "time_leakage": False, "valid": True},
        source="fixture://anomaly/leakage.json",
        evidence="finding:drift:future-label",
    )
    return family(KIND_ANOMALY, (pos_item, hard_item, short_item, leak_item))


def domain_negative_family() -> GoldFamily:
    """Same-name, invoice, and reference cases that must not imply identity or delivery."""
    same_name = {
        "implication": "identity",
        "left_id": "person:alpha",
        "predicate": "pred.same-name-as",
        "right_id": "person:gamma",
        "valid": False,
    }
    delivery = {
        "claims_delivery": True,
        "implication": "delivery",
        "stage": "invoiced",
        "valid": False,
    }
    references = {
        "implication": "part-of",
        "predicate": "pred.references",
        "valid": False,
    }
    same_item = item(
        item_id="domain-same-name-final",
        item_kind=KIND_DOMAIN_NEGATIVE,
        split=SPLIT_FINAL,
        gold_ref="gold:domain-same-name:final",
        gold=same_name,
        positive=same_name,
        negative={**same_name, "implication": "identity", "valid": True},
        source="fixture://domain/same-name.json",
        evidence="pred.same-name-as",
        label="Fixture Person",
    )
    invoice_item = item(
        item_id="domain-invoice-not-delivery-tuning",
        item_kind=KIND_DOMAIN_NEGATIVE,
        split=SPLIT_TUNING,
        gold_ref="gold:domain-invoice:tuning",
        gold=delivery,
        positive=delivery,
        negative={**delivery, "valid": True},
        source="fixture://domain/invoice-stage.json",
        evidence="stage:invoiced",
    )
    ref_item = item(
        item_id="domain-references-not-part-of-final",
        item_kind=KIND_DOMAIN_NEGATIVE,
        split=SPLIT_FINAL,
        gold_ref="gold:domain-references:final",
        gold=references,
        positive=references,
        negative={**references, "implication": "part-of", "valid": True},
        source="fixture://domain/references.json",
        evidence="pred.references",
    )
    return family(KIND_DOMAIN_NEGATIVE, (same_item, invoice_item, ref_item))

"""Shared builders for compact frozen evaluation items."""

from collections.abc import Mapping

from arxiv_int.evaluation.fixture_kinds import (
    FIXTURE_CONTRACT_VERSION,
    FIXTURE_DATASET_ID,
    FIXTURE_GENERATION_ID,
    SCHEMA_VERSION,
    SPLIT_FINAL,
    SPLIT_TUNING,
)
from arxiv_int.evaluation.fixture_model import EvaluationItem, GoldFamily, item_from_payload


def provenance(source: str, evidence: str, **extra: str) -> dict[str, str]:
    """Build the required provenance map for one item."""
    payload = {"evidence": evidence, "source": source}
    payload.update(extra)
    return payload


def item(
    *,
    item_id: str,
    item_kind: str,
    split: str,
    gold_ref: str,
    gold: Mapping[str, object],
    positive: Mapping[str, object],
    negative: Mapping[str, object],
    source: str,
    evidence: str,
    query_text: str | None = None,
    label: str | None = None,
    extra_provenance: Mapping[str, str] | None = None,
) -> EvaluationItem:
    """Construct one typed frozen item."""
    payload = {
        "contract_version": FIXTURE_CONTRACT_VERSION,
        "dataset_id": FIXTURE_DATASET_ID,
        "generation_id": FIXTURE_GENERATION_ID,
        "gold": dict(gold),
        "gold_ref": gold_ref,
        "item_id": item_id,
        "item_kind": item_kind,
        "label": label,
        "negative": dict(negative),
        "positive": dict(positive),
        "provenance": provenance(source, evidence, **dict(extra_provenance or {})),
        "query_text": query_text,
        "split": split,
    }
    return item_from_payload(payload)


def family(kind: str, items: tuple[EvaluationItem, ...]) -> GoldFamily:
    """Wrap items as a version-1 family document."""
    return GoldFamily(kind, SCHEMA_VERSION, items)


def pair_splits(
    *,
    item_kind: str,
    stem: str,
    gold: Mapping[str, object],
    positive: Mapping[str, object],
    negative: Mapping[str, object],
    source: str,
    evidence: str,
    query_text: str | None = None,
    label: str | None = None,
    extra_gold: Mapping[str, object] | None = None,
    extra_positive: Mapping[str, object] | None = None,
    extra_query: str | None = None,
) -> tuple[EvaluationItem, EvaluationItem]:
    """Return one tuning item and a distinct final sibling."""
    if extra_gold is None:
        final_gold = {**dict(gold), "split_mark": "final"}
        final_positive = dict(positive)
        final_negative = dict(negative)
    else:
        final_gold = dict(extra_gold)
        final_positive = dict(extra_positive) if extra_positive is not None else dict(extra_gold)
        final_negative = {**dict(negative), "split_mark": "final"}
    tuning = item(
        item_id=f"{stem}-tuning",
        item_kind=item_kind,
        split=SPLIT_TUNING,
        gold_ref=f"gold:{stem}:tuning",
        gold=gold,
        positive=positive,
        negative=negative,
        source=source,
        evidence=evidence,
        query_text=query_text,
        label=label,
    )
    final = item(
        item_id=f"{stem}-final",
        item_kind=item_kind,
        split=SPLIT_FINAL,
        gold_ref=f"gold:{stem}:final",
        gold=final_gold,
        positive=final_positive,
        negative=final_negative,
        source=source,
        evidence=f"{evidence}-final",
        query_text=extra_query or (f"{query_text} final" if query_text else None),
        label=label,
    )
    return tuning, final
